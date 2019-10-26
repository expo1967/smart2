#!C:\Perl64\bin\perl.exe -w

######################################################################
#
# File      : smart.cgi
#
# Author    : Barry Kimelman
#
# Created   : October 20, 2019
#
# Purpose   : CGI script to implement smart contract management
#
# Notes     : All output, including status code, sent back to the client
#             is in XML format.
#
######################################################################

use strict;
use warnings;
use CGI qw(:standard);
use CGI::Carp qw(warningsToBrowser fatalsToBrowser);
use DBI;
use Time::Local;
use File::Basename;
use Data::Dumper;
use FindBin;
use lib $FindBin::Bin;

require "database.pl";

my $cgi;
my $script_name = "";
my $dbh;
my $smart_users_table = "smart_users";
my $smart_users_history_table = "smart_users_history";
my $response_data = "";
my %users_info = ();
my %uid_to_name = ();

my @user_columns = (
	"mod_date" , "username" , "password" , "first_name" , "last_name" ,
	"email" , "phone" , "priv_level" , "balance1" , "balance" ,
	"status" , "comment"
);

my @user_modify_columns = (
	"new_password" , "first_name" , "last_name" ,
	"email" , "phone" , "priv_level" , "comment"
);

my %data_types = (
	"mod_date" => "TIMEDATE" , "username" => "char" , "password" => "password" , "first_name" => "char" , "last_name" => "char" ,
	"email" => "char" , "phone" => "char" , "priv_level" => "int" , "balance1" => "int" , "balance" => "int" ,
	"status" => "char" , "comment" => "char"
);

# Translate CGI script parameters to actual database table column names
my %fields_map = (
	"newuser" => "username" ,
	"newpassword" => "password" ,
	"first_name" => "first_name" ,
	"last_name" => "last_name" ,
	"email" => "email" ,
	"phone" => "phone" ,
	"priv_level" => "priv_level" ,
	"balance1" => "balance1" ,
	"comment" => "comment" ,
);

my %transactions = ();
my @transaction_columns = (
	"id" , "mod_date" , "user1" , "user1_balance" , "user2" , "user2_balance" ,
	"operation" , "status" , "amount"
);

my $username;
my $uid;
my $password;

my %status0 = (
	"status_code" => 0 ,
	"error_message" => "" ,
	"error_details" => ""
);
my %status1 = ();

my %functions = (
	"users" => { "function" => \&show_users , "admin" => 0 } ,
	"void" => { "function" => \&void_trans , "admin" => 1 } ,
	"send" => { "function" => \&send_money , "admin" => 1 } ,
	"hist" => { "function" => \&show_trans , "admin" => 0 } ,
	"delete_user" => { "function" => \&delete_user , "admin" => 1 } ,
	"get_user" => { "function" => \&get_user , "admin" => 1 } ,
	"modify_user" => { "function" => \&modify_user , "admin" => 1 } ,
	"add_user" => { "function" => \&add_user , "admin" => 1 } ,
);

######################################################################
#
# Function  : send_response
#
# Purpose   : Send a response
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : (nothing)
#
# Example   : send_response();
#
# Notes     : Script execution is terminated after the response is sent
#
######################################################################

sub send_response
{
	print qq~
<RESPONSE>
	<status_code>${status1{'status_code'}}</status_code>
	<error_message>${status1{'error_message'}}</error_message>
	<error_details>${status1{'error_details'}}</error_details>
~;
	if ( $response_data ne "" ) {
		print "$response_data\n";
	} # IF

	print qq~
</RESPONSE>
~;

	if ( $dbh ) {
		$dbh->disconnect();
	} # IF

	exit 0;
} # end of send_response

######################################################################
#
# Function  : read_from_database
#
# Purpose   : Read data from the database
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : (nothing)
#
# Example   : read_from_database();
#
# Notes     : Script processing is terminated if an error occurs
#
######################################################################

sub read_from_database
{
	my ( $sql , $sth , $ref , $user_name , $id );

	$sql =<<SQL;
select id,mod_date,username,aes_decrypt(password,'pizza') password,first_name,last_name,
email,phone,priv_level,balance1,balance,status,comment
from ${smart_users_table}
SQL
	$sth = $dbh->prepare($sql);
	unless ( defined $sth ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Can't prepare sql for reading users table";
		$status1{"error_details"} = $DBI::errstr;
		send_response();
	} # UNLESS
	unless ( $sth->execute() ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Can't execute sql for reading users table";
		$status1{"error_details"} = $DBI::errstr;
		send_response();
	} # UNLESS
	$ref = $sth->fetchrow_hashref();
	%users_info = ();
	%uid_to_name = ();
	while ( defined $ref ) {
		$user_name = $ref->{"username"};
		$uid_to_name{$ref->{"id"}} = $user_name;
		foreach my $column ( @user_columns ) {
			$users_info{$user_name}{$column} = $ref->{$column};
		} # FOREACH
		$users_info{$user_name}{"id"} = $ref->{"id"};
		$ref = $sth->fetchrow_hashref();
	} # WHILE
	$sth->finish();

	$sql =<<SQL;
select * from ${smart_users_history_table}
SQL
	$sth = $dbh->prepare($sql);
	unless ( defined $sth ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Can't prepare sql for reading transactions table";
		$status1{"error_details"} = $DBI::errstr;
		send_response();
	} # UNLESS
	unless ( $sth->execute() ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Can't execute sql for reading transactions table";
		$status1{"error_details"} = $DBI::errstr;
		send_response();
	} # UNLESS
	$ref = $sth->fetchrow_hashref();
	%transactions = ();
	while ( defined $ref ) {
		$id = $ref->{"id"};
		foreach my $column ( @transaction_columns ) {
			$transactions{$id}{$column} = $ref->{$column};
		} # FOREACH
		$ref = $sth->fetchrow_hashref();
	} # WHILE

	return 0;
} # end of read_from_database

######################################################################
#
# Function  : validate_user_info
#
# Purpose   : Validate the specified username and password
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : validate_user_info();
#
# Notes     : (none)
#
######################################################################

sub validate_user_info
{
	my ( $count , $index , $ref );

	$username = $cgi->param("username");
	$password = $cgi->param("password");
	unless ( defined $username && $username =~ m/\S/ && defined $password && $password =~ m/\S/ ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Missing username and/or password";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$ref = $users_info{lc $username};
	unless ( defined $ref ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Invalid username";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$uid = $ref->{"id"};
	unless ( $password eq $ref->{"password"} ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Invalid password for '$username'";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	if ( $ref->{"status"} ne "active" ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "User '$username' status is not 'active'";
		$status1{"error_details"} = "";
		send_response();
	} # IF

	return 0;
} # end of validate_user_info

######################################################################
#
# Function  : show_users
#
# Purpose   : Return list of users
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : show_users();
#
# Notes     : (none)
#
######################################################################

sub show_users
{
	my ( $count , $index , $ref );

	$response_data = "";
	foreach my $user ( keys %users_info ) {
		if ( $users_info{$username}{"priv_level"} && $username ne $user ) {
			next;
		} # IF
		$response_data .= "<USER>\n";
		foreach my $column ( @user_columns ) {
			$response_data .= "<$column>$users_info{$user}{$column}</$column>\n";
		} # FOREACH
		$response_data .= "</USER>\n";
	} # FOREACH
	$status1{"status_code"} = 0;
	$status1{"error_message"} = "SUCCESS";
	$status1{"error_details"} = "";
	send_response();

	return 0;
} # end of show_users

######################################################################
#
# Function  : show_trans
#
# Purpose   : Return list of transactions
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : show_trans();
#
# Notes     : (none)
#
######################################################################

sub show_trans
{
	my ( $count , $index , $ref , %hash , %hash2 );
	my ( $user1, $user2 , $value );

	$response_data = "";
	$count = 0;
	foreach my $id ( keys %transactions ) {
		$ref = $transactions{$id};
		$user1 = $uid_to_name{$ref->{"user1"}};
		$user2 = $uid_to_name{$ref->{"user2"}};
		if ( $users_info{$username}{"priv_level"} &&
					$user1 ne $username && $user2 ne $username ) {
			next;
		} # IF
		$count += 1;
		$response_data .= "<TRANS>\n";
		foreach my $column ( @transaction_columns ) {
			$value = $ref->{$column};
			if ( $column eq "user1" ) {
				$value = $user1;
			} elsif ( $column eq "user2" ) {
				$value = $user2;
			} # ELSIF
			$response_data .= "<$column>$value</$column>\n";
		} # FOREACH
		$response_data .= "</TRANS>\n";
	} # FOREACH
	$response_data .= "<NUM_TRANS>$count</NUM_TRANS>";
	$status1{"status_code"} = 0;
	$status1{"error_message"} = "SUCCESS";
	$status1{"error_details"} = "";
	send_response();

	return 0;
} # end of show_trans

######################################################################
#
# Function  : send_money
#
# Purpose   : Process command
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : send_money();
#
# Notes     : (none)
#
######################################################################

sub send_money
{
	my ( $username2 , $amount , $ref_user2 , $sql , $sth , $num_rows );
	my ( $user1_balance , $user2_balance , $user2 );

	$username2 = lc $cgi->param("username2");
	$amount = $cgi->param("amount");
	unless ( defined $username2 && $username2 =~ m/\S/ && defined $amount && $amount =~ m/\S/ ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Missing username2 and/or amount";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$ref_user2 = $users_info{$username2};
	unless ( defined $ref_user2 ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "'$username2' is not a valid username";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$user2 = $ref_user2->{"id"};
	if ( $amount =~ m/\D/ ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Amount contains non numeric chaacters";
		$status1{"error_details"} = "";
		send_response();
	} # IF
	if ( $amount > $users_info{$username}{"balance"} ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Specified amount exceeds the current balance for $username";
		$status1{"error_details"} = "";
		send_response();
	} # IF

	$user1_balance = $users_info{$username}{"balance"} - $amount;
	$sql =<<SQL;
UPDATE $smart_users_table SET balance = $user1_balance
WHERE id = $uid
SQL
	$num_rows = $dbh->do($sql);
	unless ( defined $num_rows ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "UPDATE failed for user $username";
		$status1{"error_details"} = "$DBI::errstr";
		send_response();
	} # UNLESS

	$user2_balance = $ref_user2->{"balance"} + $amount;
	$sql =<<SQL;
UPDATE $smart_users_table SET balance = $user2_balance
WHERE id = $user2
SQL
	$num_rows = $dbh->do($sql);
	unless ( defined $num_rows ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "UPDATE failed for user $username2";
		$status1{"error_details"} = "$DBI::errstr";
		send_response();
	} # UNLESS

	$sql =<<SQL;
INSERT INTO ${smart_users_history_table}
( mod_date , user1 , user1_balance , user2 , user2_balance , operation , status , amount )
VALUES ( now() , $uid , $user1_balance , $user2 , $user2_balance , "send" ,
	"active" , $amount )
SQL
	$num_rows = $dbh->do($sql);
	unless ( defined $num_rows ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Could not record transaction";
		$status1{"error_details"} = "$DBI::errstr";
		send_response();
	} # UNLESS

	$status0{"status_code"} = 1;
	$status1{"error_message"} = "Transfer of funds to '$username2' was successfull";
	$status1{"error_details"} = "";
	send_response();

	return 0;
} # end of send_money

######################################################################
#
# Function  : add_user
#
# Purpose   : Process add_user command
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : add_user();
#
# Notes     : (none)
#
######################################################################

sub add_user
{
	my ( %fields_value , $missing , $value , @missing , $sql , $sth , $num_rows );
	my ( $buffer , $ref , $errors , $data_type , $sep , @bad );

	$missing = 0;
	%fields_value = ();
	@missing = ();
	foreach my $fieldname ( keys %fields_map ) {
		$value = $cgi->param($fieldname);
		unless ( defined $value && $value =~ m/\S/ ) {
			push @missing,$fieldname;
			$missing += 1;
		} # UNLESS
		else {
			$fields_value{$fields_map{$fieldname}} = $value;
		} # ELSE
	} # FOREACH
	if ( $missing > 0 ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Some field values were missing";
		$status1{"error_details"} = join(" , ",@missing);
		send_response();
	} # IF
	$value = lc $fields_value{"username"};
	$fields_value{"username"} = $value;
	$ref = $users_info{$value};
	if ( defined $ref ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "User '$value' already exists";
		$status1{"error_details"} = "";
		send_response();
	} # IF

	$status1{"status_code"} = 0;
	$status1{"error_message"} = "SUCCESS";
	$status1{"error_details"} = "All field values were received";
	##  send_response();

	$buffer = join(" , ",@user_columns);
	$sql =<<SQL;
INSERT INTO ${smart_users_table}
( $buffer )
VALUES (
SQL

	$sep = " ";
	$errors = 0;
	@bad = ();
	$fields_value{"balance"} = $fields_value{"balance1"};
	$fields_value{"status"} = "active";
	foreach my $colname ( @user_columns ) {
		$data_type = $data_types{$colname};
		if ( $data_type =~ m/time/i ) {
			$sql .= $sep . "now()";
		} elsif ( $data_type eq "int" ) {
			$value = $fields_value{$colname};
			if ( $value =~ m/\D/ ) {
				$errors += 1;
				push @bad,$colname;
			} # IF
			else {
				$sql .= $sep . $value;
			} # ELSE
		} elsif ( $data_type eq "password" ) {
##  VALUES ( now() , aes_encrypt('$new_data','$secret_key')
			$value = $fields_value{$colname};
			$value = "aes_encrypt('$value','pizza')";
			$sql .= $sep . $value;
		} else {
			$value = $fields_value{$colname};
			$sql .= $sep . '"' . $value . '"';
		} # ELSE
		$sep = " , ";
	} # FOREACH
	$sql .= ")";
	if ( $errors > 0 ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Some field values contained invalid data";
		$status1{"error_details"} = join(" , ",@bad);
		send_response();
	} # IF

	$num_rows = $dbh->do($sql);
	unless ( defined $num_rows ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Could not create new user";
		$status1{"error_details"} = "$sql\n$DBI::errstr";
		send_response();
	} # UNLESS

	$status1{"status_code"} = 0;
	$status1{"error_message"} = "SUCCESS";
	$status1{"error_details"} = "new user successfully created";
	send_response();

	return 0;
} # end of add_user

######################################################################
#
# Function  : void_trans
#
# Purpose   : Process "void" command
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : void_trans();
#
# Notes     : (none)
#
######################################################################

sub void_trans
{
	my ( $id , $ref , $sql , $num_rows , $amount );
	my ( $ref_user , $balance , $old_status );

	$id = $cgi->param("trans_id");
	unless ( defined $id && $id =~ m/^\d+$/ ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Missing or invalid transaction id";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$ref = $transactions{$id};
	unless ( defined $ref ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "$id is not a valid transaction id";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$old_status = $ref->{"status"};
	if ( $old_status eq "voided" ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Invalid void request. Transaction $id is already voided.";
		$status1{"error_details"} = "";
		send_response();
	} # IF
	$amount = $ref->{"amount"};

	$sql =<<SQL;
UPDATE ${smart_users_history_table} SET status = "voided"
WHERE id = $id
SQL
	$num_rows = $dbh->do($sql);
	unless ( defined $num_rows ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Could not update transactions table";
		$status1{"error_details"} = "$DBI::errstr";
		send_response();
	} # UNLESS

	$ref_user = $users_info{$ref->{"user1"}};
	update_user_balance($ref_user,"inc",$amount);

	$ref_user = $users_info{$ref->{"user2"}};
	update_user_balance($ref_user,"dec",$amount);

	$status1{"status_code"} = 0;
	$status1{"error_message"} = "SUCCCESS";
	$status1{"error_details"} = "Transaction with id $id has been voided";
	send_response();

	return 0;
} # end of void_trans

######################################################################
#
# Function  : update_user_balance
#
# Purpose   : Update the database users table balance
#
# Inputs    : $_[0] - ref to hash describing update operation
#             $_[1] - "inc"  or "dec"
#             $_[2] - amount of the adjustment
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : update_user_balance($users_info{$user},"inc",100);
#
# Notes     : (none)
#
######################################################################

sub update_user_balance
{
	my ( $ref_user , $inc_dec , $amount ) = @_;
	my ( $sql , $balance , $num_rows );

	if ( $inc_dec eq "inc" ) {
		$balance = $ref_user->{"balance"} + $amount;
	} # IF
	else {
		$balance = $ref_user->{"balance"} - $amount;
	} # ELSE
	$sql =<<SQL;
UPDATE $smart_users_table SET balance = $balance
WHERE username = "$ref_user->{'username'}"
SQL
	$num_rows = $dbh->do($sql);
	unless ( defined $num_rows ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Could not update users table for $ref_user->{'username'} with\n$sql";
		$status1{"error_details"} = "$DBI::errstr";
		send_response();
	} # UNLESS

	return 0;
} # end of update_user_balance

######################################################################
#
# Function  : delete_user
#
# Purpose   : Process delete user command
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : delete_user();
#
# Notes     : (none)
#
######################################################################

sub delete_user
{
	my ( $old_user , $ref_user , $sql , $num_rows );

	$old_user = lc $cgi->param("old_user");
	unless ( defined $old_user && $old_user =~ m/\S/ ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Missing old_user";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$ref_user = $users_info{$old_user};
	unless ( defined $ref_user ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "'$old_user' is not an existing user";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	if ( $ref_user->{"status"} eq "expired" ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "'$old_user' is already expired";
		$status1{"error_details"} = "";
		send_response();
	} # IF
	$sql =<<SQL;
UPDATE $smart_users_table SET status = "expired"
WHERE username = '$old_user'
SQL
	$num_rows = $dbh->do($sql);
	unless ( defined $num_rows ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "UPDATE failed for user $old_user";
		$status1{"error_details"} = "$DBI::errstr";
		send_response();
	} # UNLESS

	$status1{"status_code"} = 0;
	$status1{"error_message"} = "SUCCESS";
	$status1{"error_details"} = "'$old_user' successfully deleted";
	send_response();

	return 0;
} # end of delete_user

######################################################################
#
# Function  : get_user
#
# Purpose   : Return information for a specific user
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : get_user();
#
# Notes     : (none)
#
######################################################################

sub get_user
{
	my ( $old_user , $ref_user , $sql , $num_rows );

	$old_user = lc $cgi->param("old_user");
	unless ( defined $old_user && $old_user =~ m/\S/ ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Missing old_user";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$ref_user = $users_info{$old_user};
	unless ( defined $ref_user ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "'$old_user' is not an existing user";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	if ( $ref_user->{"status"} eq "expired" ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "'$old_user' is already expired";
		$status1{"error_details"} = "";
		send_response();
	} # IF
	$response_data = "";
	foreach my $column ( @user_modify_columns ) {
		if ( $column eq "new_password" ) {
			$response_data .= "<$column>$ref_user->{'password'}</$column>\n";
		} # IF
		else {
			$response_data .= "<$column>$ref_user->{$column}</$column>\n";
		} # ELSE
	} # FOREACH
	send_response();

	return 0;
} # end of get_user

######################################################################
#
# Function  : modify_user
#
# Purpose   : Process a modify user request
#
# Inputs    : (none)
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : modify_user();
#
# Notes     : (none)
#
######################################################################

sub modify_user
{
	my ( $old_user , $ref_user , $sql , $num_rows , $count , $sep , $data_type , $ref );
	my ( $value , @modified );

	$old_user = lc $cgi->param("old_user");
	unless ( defined $old_user && $old_user =~ m/\S/ ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "Missing old_user";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	$ref_user = $users_info{$old_user};
	unless ( defined $ref_user ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "'$old_user' is not an existing user";
		$status1{"error_details"} = "";
		send_response();
	} # UNLESS
	if ( $ref_user->{"status"} eq "expired" ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "'$old_user' is currently expired and can't be modified";
		$status1{"error_details"} = "";
		send_response();
	} # IF

	$sql ="UPDATE $smart_users_table SET ";
	$sep = " ";
	$count = 0;
	@modified = ();
	foreach my $column ( @user_modify_columns ) {
		$value = $cgi->param($column);
		if ( defined $value && $value =~ m/\S/ ) {
			$count += 1;
			push @modified,$column;
			$data_type = ($column eq "new_password") ? "password" : $data_types{$column};
			if ( $data_type eq "int" ) {
				$sql .= $sep . "$column = $value";
			} elsif ( $data_type eq "password" ) {
				$value = "aes_encrypt('$value','pizza')";
				$sql .= $sep . "password = $value";
			} else {
				$value = '"' . $value . '"';
				$sql .= $sep . "$column = $value";
			} # ELSE
			$sep = " , ";
		} # IF
	} # FOREACH
	if ( $count == 0 ) {
		$status1{"status_code"} = 1;
		$status1{"error_message"} = "No new field values were detected";
		$status1{"error_details"} = "request ignored";
		send_response();
	} # IF
	else {
		$sql .= " WHERE id = $ref_user->{'id'}";
		$num_rows = $dbh->do($sql);
		unless ( defined $num_rows ) {
			$status1{"status_code"} = 1;
			$status1{"error_message"} = "UPDATE failed for user $old_user\n$sql";
			$status1{"error_details"} = "$DBI::errstr";
			send_response();
		} # UNLESS
		$status0{"status_code"} = 0;
		$status1{"error_message"} = "UPDATE succeeded for user $old_user";
		$status1{"error_details"} = "";
		send_response();
	} # ELSE

	return 0;
} # end of modify_user

######################################################################
#
# Function  : MAIN
#
# Purpose   : CGI script to implement smart contract management
#
# Inputs    : @ARGV - array of parameters
#
# Output    : HTML
#
# Returns   : 0 --> success , non-zero --> failure
#
# Example   : (none)
#
# Notes     : (none)
#
######################################################################

my ( $buffer , $status , $errmsg , $function , $ref , %hash , $func );

$script_name = basename($0);

$cgi = new CGI;

print "Content-Type: text/xml\r\n";   # header tells client you send XML
print "\r\n";                         # empty line is required between headers
                                      #   and body

%status1 = %status0;
$response_data = "";

#---------------------#
# Connect to database #
#---------------------#
$dbh = mysql_connect_to_db("qwlc","127.0.0.1","root","archer-nx01",undef,\$errmsg);
unless ( defined $dbh ) {
	$status1{"status_code"} = 1;
	$status1{"error_message"} = "Can't connect to the database";
	$status1{"error_details"} = $errmsg;
	exit 0;
} # UNLESS

read_from_database();
validate_user_info();
$function = $cgi->param("function");
unless ( defined $function && $function =~ m/\S/ ) {
	$status1{"status_code"} = 1;
	$status1{"error_message"} = "Missing function code";
	$status1{"error_details"} = "";
	send_response();
} # UNLESS
$ref = $functions{$function};
unless ( defined $ref ) {
	$status1{"status_code"} = 1;
	$status1{"error_message"} = "'$function' is not a valid function";
	$status1{"error_details"} = "";
	send_response();
} # UNLESS
%hash = %$ref;
if ( $hash{'admin'} && $users_info{$username}{"priv_level"} ) {
	$status1{"status_code"} = 1;
	$status1{"error_message"} = "'$username' is not authorized to use the '$function' command";
	$status1{"error_details"} = "";
	send_response();
} # IF
$func = $hash{"function"};
$func->();

exit 0;
