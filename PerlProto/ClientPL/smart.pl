#!C:\Perl64\bin\perl.exe -w

######################################################################
#
# File      : smart.pl
#
# Author    : Barry Kimelman
#
# Created   : October 21, 2019
#
# Purpose   : Smart contracts client program
#
# Notes     : (none)
#
######################################################################

use strict;
use warnings;
use Getopt::Std;
use Data::Dumper;
use LWP::UserAgent;
use LWP::Protocol::https;
use File::Basename;
use XML::Simple;
use Term::ReadKey;
use URI;
use URI::Escape;
use FindBin;
use lib $FindBin::Bin;

require "display_pod_help.pl";
require "mysql_utils.pl";
require "print_lists.pl";
require "comma_format.pl";

my %options = ( "d" => 0 , "h" => 0 );
##  my $url_part_1 = "http://localhost:88/cgi-bin/smart.cgi?";
my $url_part_1 = "http://localhost:88/cgi-bin2/smart.cgi?";
my $server_response;
my $server_decoded_data;
my @server_decoded_lines;
my $server_num_decoded_bytes;
my $server_xml_data;
my $pager = "more";
my $script_name;

my @user_columns = (
	"mod_date" , "username" , "password" , "first_name" , "last_name" ,
	"email" , "phone" , "priv_level" , "balance1" , "balance" ,
	"status" , "comment"
);

my @user_modify_columns = (
	"first_name" , "last_name" , "new_password" ,
	"email" , "phone" , "priv_level" , "comment"
);

my @user_columns_labels = (
	"Modification Date" , "Username" , "Password" , "First Name" , "Last Name" ,
	"Email" , "Phone" , "Privilege Level" , "Initial Balance" , "Current Balance" ,
	"Status" , "Comment"
);

my @transaction_columns = (
	"mod_date" , "user1" , "user1_balance" , "user2" , "user2_balance" ,
	"operation" , "status" , "amount"
);

my $help_show_users =<<HELP_SHOW_USERS;
This command displays information for the defined users. Only an administartor will
see information for all the users. Non-admin users will only see information
for themselves.
HELP_SHOW_USERS

my $help_send =<<HELP_SEND;
Send money to another user.

ex : SCRIPT_NAME send username1 password1 username2 amount

Send the specified amount (in pennies) from username1 to username2
HELP_SEND

my $help_help =<<HELP_HELP;
Display command help information
HELP_HELP

my $help_hist =<<HELP_HIST;
This command displays transaction history information. Only an administartor will
see information for all the users. Non-admin users will only see information
for themselves.
HELP_HIST

my $help_adduser =<<HELP_ADDGUI;
This privileged command provides a prompt and reply interface to create a new user.

e.g. : SCRIPT_NAME myname mypassword adduser
HELP_ADDGUI

my $help_moduser =<<HELP_MODGUI;
This privileged command provides a prompt and reply interface to modify an existing user.

e.g. : SCRIPT_NAME myname mypassword moduser
HELP_MODGUI

my $help_void =<<HELP_VOID;
Void a transaction. The balances of the 2 users will be adjusted by the amount of
the transaction to make it look like the transaction never happened.

e.g. SCRIPT_NAME myname mypassword transaction_id
HELP_VOID

my %functions = (
	"users" => [ \&show_users , 'list defined users' , \$help_show_users ] ,
	"send" => [ \&send_money , 'send money to another user' , \$help_send ] ,
	"hist" => [ \&show_hist , 'display transactions history' , \$help_hist ] ,
	"void" => [ \&void_trans , 'void a transaction' , \$help_void ] ,
  	"adduser" => [ \&adduser , 'create a new user with prompting (admin only)' , \$help_adduser ],
  	"moduser" => [ \&moduser , 'modify an existing user with prompting (admin only)' , \$help_moduser ],
	"help" => [ \&help , 'display commands help' , \$help_help ]
);

my @fields_order = (
	"username" , "password" , "first_name" , "last_name" , "email" , "phone" ,
	"priv_level" , "balance1" , "comment"
);

my @modify_fields_order = (
	"password" , "first_name" , "last_name" , "email" , "phone" ,
	"priv_level" , "comment"
);

my %input_fields = (
	"username" =>  { "required" => "yes" , "title" => "Username" , "data_type" => "string" , "value" => "" } ,
	"password" =>  { "required" => "yes" , "title" => "Password" , "data_type" => "password" , "value" => "" } ,
	"first_name" =>  { "required" => "yes" , "title" => "First Name" , "data_type" => "string" , "value" => "" } ,
	"last_name" =>  { "required" => "yes" , "title" => "Last Name" , "data_type" => "string" , "value" => "" } ,
	"email" =>  { "required" => "yes" , "title" => "Email" , "data_type" => "string" , "value" => "" } ,
	"phone" =>  { "required" => "yes" , "title" => "Phone" , "data_type" => "string" , "value" => "" } ,
	"priv_level" =>  { "required" => "yes" , "title" => "Privilege Level" , "data_type" => "int" , "value" => "" } ,
	"balance1" =>  { "required" => "yes" , "title" => "Initial Balance" , "data_type" => "int" , "value" => "" } ,
	"comment" =>  { "required" => "yes" , "title" => "Comment" , "data_type" => "string" , "value" => "" }
);

my $function;
my $username;
my $password;

######################################################################
#
# Function  : debug_print
#
# Purpose   : Optionally print a debugging message.
#
# Inputs    : @_ - array of strings comprising message
#
# Output    : (none)
#
# Returns   : nothing
#
# Example   : debug_print("Process the files : ",join(" ",@xx),"\n");
#
# Notes     : (none)
#
######################################################################

sub debug_print
{
	if ( $options{"d"} ) {
		print join("",@_);
	} # IF

	return;
} # end of debug_print

######################################################################
#
# Function  : send_request_to_server
#
# Purpose   : Send a request to the server
#
# Inputs    : $_[0] - buffer containing URL  parameters
#
# Output    : appropriate messages
#
# Returns   : IF problem THEN negative ELSE zero
#
# Example   : $status = send_request_to_server($parms);
#
# Notes     : (none)
#
######################################################################

sub send_request_to_server
{
	my ( $parms_data ) = @_;
	my ( $url , $status , $ua );

	$url = $url_part_1 . $parms_data;
	debug_print("Send the following request\n$url\n");
	$ua = LWP::UserAgent->new;
	$ua->timeout(20);
	$ua->env_proxy;
	$server_response = $ua->get($url);
	unless ( $server_response->is_success ) {
		die("$url :\n",Dumper($server_response->status_line));
	} # UNLESS
	$server_decoded_data = $server_response->decoded_content;
	debug_print("Response from server\n$server_decoded_data\n");
	@server_decoded_lines = split(/\n/,$server_decoded_data);
	$server_num_decoded_bytes = length $server_decoded_data;

	$Data::Dumper::Indent = 1;  # this is a somewhat more compact output style
	$Data::Dumper::Sortkeys = 1; # sort alphabetically

	$server_xml_data = XMLin($server_decoded_data , SuppressEmpty => '');
	unless ( defined $server_xml_data ) {
		die("XMLin failed for server response data\n");
	} # UNLESS
	debug_print("Parsed XML data from server is:\n",Dumper($server_xml_data));

	$status = $server_xml_data->{"status_code"};
	if ( $status ) {
		warn("Command failed with status code $status\n");
		print "$server_xml_data->{'error_message'}\n";
		print "$server_xml_data->{'error_details'}\n";
		die("\nGoodbye ...\n");
	} # IF

	return 0;
} # end of send_request_to_server

######################################################################
#
# Function  : format_dollars
#
# Purpose   : Format a binary current amount into a printable string
#
# Inputs    : $_[0] - amount in pennies
#
# Output    : appropriate mesages
#
# Returns   : Formatted dollars and cents value;
#
# Example   : $dollars = format_dollars($pennies);
#
# Notes     : (none)
#
######################################################################

sub format_dollars
{
	my ( $pennies ) = @_;
	my ( $dollars , @parts );

	$dollars = sprintf "%.2f",$pennies/100.0;
	@parts = split(/\./,$dollars);
	$dollars = '$' . comma_format($parts[0]) . '.' . $parts[1];

	return $dollars;
} # end of format_dollars

######################################################################
#
# Function  : read_password
#
# Purpose   : Read a password without echoing the typed characters
#
# Inputs    : $_[0] - prompt
#
# Output    : specified prompt
#
# Returns   : the typed password
#
# Example   : $password = read_password("Enter your password : ");
#
# Notes     : (none)
#
######################################################################

sub read_password
{
	my ( $prompt ) = @_;
	my ( $password );

	ReadMode( "noecho");
	print "$prompt";
	$password = <STDIN>;
	chomp $password;
	ReadMode ("original") ;

	return $password;
} # end of read_password

######################################################################
#
# Function  : show_users
#
# Purpose   : Process a "show users" command
#
# Inputs    : (none)
#
# Output    : command results from server
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
	my ( $parms , $status , $ref , $ref_users , $index , @users_info );
	my ( $index2 , $maxlen , $value );

	$parms = "function=$function&username=$username&password=$password";
	$status = send_request_to_server($parms);
	$ref_users = $server_xml_data->{"USER"};
	$ref = ref $ref_users;
	if ( $ref eq "ARRAY" ) {
		@users_info = @$ref_users;
	} # IF
	else {
		@users_info = ( $ref_users );
	} # ELSE
	unless ( open(PIPE,"|$pager") ) {
		die("open of pipe to '$pager' failed : $!\n");
	} # UNLESS

	for ( $index = 0 ; $index <= $#users_info ; ++$index ) {
		print PIPE "\n";
		$ref = $users_info[$index];
		$maxlen = (reverse sort { $a <=> $b} map { length $_ } @user_columns_labels)[0];
		for ( $index2 = 0 ; $index2 <= $#user_columns ; ++$index2 ) {
			$value = $ref->{$user_columns[$index2]};
			if ( $user_columns[$index2] =~ m/balance/i ) {
				##  $value = '$' . sprintf "%.2f",$value/100.0;
				$value = format_dollars($value);
			} # IF
			printf PIPE "%-${maxlen}.${maxlen}s : %s\n",$user_columns_labels[$index2],
							$value;
		} # FOR
	} # FOR
	close PIPE;

	return;
} # end of show_users

######################################################################
#
# Function  : show_hist
#
# Purpose   : Process a "hist" command
#
# Inputs    : (none)
#
# Output    : command results from server
#
# Returns   : nothing
#
# Example   : show_hist();
#
# Notes     : (none)
#
######################################################################

sub show_hist
{
	my ( $parms , $status , $ref , $ref_trans , $index , $index2 , @ids );
	my ( $maxlen , $value , $column , $num_trans , %hash , %hash2 , $id );
	my ( @dates , @user1 , @user1_balance , @user2 , @user2_balance );
	my ( @operation , @status , @amount , @arrays , @headers );

	$parms = "function=$function&username=$username&password=$password";
	$status = send_request_to_server($parms);

	$num_trans = $server_xml_data->{"NUM_TRANS"};
	if ( $num_trans == 0 ) {
		print "No transaction data currently exists\n";
		return;
	} # IF

	$ref_trans = $server_xml_data->{"TRANS"};
	if ( $num_trans == 1 ) {
		%hash = %$ref_trans;
		$id = $hash{"id"};
		delete $hash{"id"};
		%hash2 = ( $id => \%hash );
	} # IF
	else {
		%hash2 = %$ref_trans;
	} # ELSE

	unless ( open(PIPE,"|$pager") ) {
		die("open of pipe to '$pager' failed : $!\n");
	} # UNLESS
	print PIPE "NUmber of transactions = $num_trans\n\n";

	@dates = ();
	@user1 = ();
	@user1_balance = ();
	@user2 = ();
	@user2_balance = ();
	@operation = ();
	@status = ();
	@amount = ();
	$maxlen = (reverse sort { $a <=> $b} map { length $_ } @transaction_columns)[0];
	@ids = keys %hash2;

	for ( $index = 0 ; $index < $num_trans ; ++$index ) {
		$id = $ids[$index];
		$ref = $hash2{$id};
		push @dates,$ref->{'mod_date'};
		push @user1,$ref->{'user1'};
		push @user1_balance,format_dollars($ref->{'user1_balance'});
		push @user2,$ref->{'user2'};
		push @user2_balance,format_dollars($ref->{'user2_balance'});
		push @operation,$ref->{'operation'};
		push @amount,format_dollars($ref->{'amount'});
		push @status,$ref->{'status'};
	} # FOR
	@headers = ( "Id" , "Date" , "User 1" , "User 1 Balance", "User 2" , "User 2 Balance" ,
					"Operation" , "Status" , "Amount" );
	@arrays = ( \@ids , \@dates , \@user1 , \@user1_balance , \@user2 , \@user2_balance ,
					\@operation , \@status , \@amount );
	print_lists( \@arrays , \@headers , '=' , \*PIPE);
	close PIPE;

	return;
} # end of show_hist

######################################################################
#
# Function  : send_money
#
# Purpose   : Process a "send" command
#
# Inputs    : (none)
#
# Output    : appropriate mesages
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
	my ( $status , $parms );

	unless ( 2 == scalar @ARGV ) {
		print "Usage : $script_name myname mypassword send username amount\n";
	} # UNLESS
	else {
		$parms = "function=$function&username=$username&password=$password&username2=$ARGV[0]&amount=$ARGV[1]";
		$status = send_request_to_server($parms);
	} # ELSE
	print "$server_xml_data->{'error_message'}\n";
	print "$server_xml_data->{'error_details'}\n";

	return 0;
} # end of send_money

######################################################################
#
# Function  : help
#
# Purpose   : Process a "help" command
#
# Inputs    : (none)
#
# Output    : appropriate mesages
#
# Returns   : nothing
#
# Example   : help();
#
# Notes     : (none)
#
######################################################################

sub help
{
	my ( $status , @cmds , $ref , @list , $buffer , $string , $maxlen );

	print "\n";
	@cmds = sort { lc $a cmp lc $b } keys %functions;
	$maxlen = (reverse sort { $a <=> $b} map { length $_ } @cmds)[0];
	if ( 0 == scalar @ARGV ) {
		print "The following commands are supported\n\n";
		foreach my $cmd ( @cmds ) {
			$ref = $functions{$cmd};
			@list = @$ref;
			$string = $list[1];
			printf "%-${maxlen}.${maxlen}s - %s\n",$cmd,$list[1];
		} # FOREACH
	} # IF
	else {
		$ref = $functions{lc $ARGV[0]};
		if ( defined $ref ) {
			@list = @$ref;
			$string = $list[1];
			$ref = $list[2];
			$buffer = $$ref;
			$buffer =~ s/SCRIPT_NAME/${script_name}/g;
			print "**  $ARGV[0]  **\n$buffer\n";
		} # IF
		else {
			print "'$ARGV[0] is not a valid command\n";
		} # ELSE
	} # ELSE

	return 0;
} # end of help

######################################################################
#
# Function  : adduser
#
# Purpose   : Process "adduser" command
#
# Inputs    : (none)
#
# Output    : appropriate messages
#
# Returns   : IF problem THEN negative ELSE zero
#
# Example   : $status = adduser();
#
# Notes     : (none)
#
######################################################################

sub adduser
{
	my ( $value , $ref_field , $data_type , $buffer , $parms , $status );

	foreach my $fieldname ( @fields_order ) {
		$ref_field = $input_fields{$fieldname};
		$data_type = $ref_field->{"data_type"};
		while ( 1 ) {
			print "Enter value for $ref_field->{'title'} : ";
			if ( $data_type eq "password" ) {
				$value = read_password("");
				print "\n";
			} # IF
			else {
				$value = <STDIN>;
			} # ELSE
			chomp $value;
			if ( $ref_field->{"required"} eq "yes" && $value !~ m/\S/ ) {
				print "No value supplied for $ref_field->{'title'} , try again\n";
				next;
			} # IF
			if ( $value eq "" ) {
				last;
			} # IF
			if ( $data_type eq "int" && $value =~ m/\D/ ) {
				print "Non numeric characters specified for $ref_field->{'title'} , try again\n";
				next;
			} # IF
			last;
		} # WHILE
		$input_fields{$fieldname}{"value"} = $value;
	} # FOREACH over input fields
	$input_fields{"balance"}{"value"} = $input_fields{"balance1"}{"value"};
	$parms = "function=add_user&username=$username&password=$password";
	foreach my $fieldname ( @fields_order ) {
		$ref_field = $input_fields{$fieldname};
		$data_type = $ref_field->{"data_type"};
		$value = $input_fields{$fieldname}{"value"};
		if ( $data_type ne "int" && $value =~ m/\s/ ) {
			$value = uri_escape($value);
		} # IF
		$parms .= "&";
		if ( $fieldname eq "username" ) {
			$parms .= "newuser";
		} elsif ( $fieldname eq "password" ) {
			$parms .= "newpassword";
		} else {
			$parms .= $fieldname;
		} # ELSE
		$parms .= "=" . $value;
	} # FOREACH

	$status = send_request_to_server($parms);
	print "$server_xml_data->{'error_message'}\n";
	print "$server_xml_data->{'error_details'}\n";

	return 0;
} # end of adduser

######################################################################
#
# Function  : moduser
#
# Purpose   : Process "moduser" command
#
# Inputs    : (none)
#
# Output    : appropriate messages
#
# Returns   : IF problem THEN negative ELSE zero
#
# Example   : $status = moduser();
#
# Notes     : (none)
#
######################################################################

sub moduser
{
	my ( $parms , $status , $old_user , $ref_field , $data_type , $value , $buffer );
	my ( $count , $modified , $title );

	if ( 0 == scalar @ARGV ) {
		print "Usage : $script_name myname mypassword moduser old_user\n";
		return;
	} # IF
	$old_user = $ARGV[0];
	$parms = "function=get_user&username=$username&password=$password&old_user=$old_user";
	$status = send_request_to_server($parms);
	print "$server_xml_data->{'error_message'}\n";
	print "$server_xml_data->{'error_details'}\n";
	$parms = "function=modify_user&username=$username&password=$password&old_user=$old_user";

	print qq~
You will be prompted for the user data fields one at a time. To keep the old value
just press the <Enter> key.

~;

	$count = 0;
	foreach my $fieldname ( @user_modify_columns ) {
		##  $ref_field = $input_fields{$fieldname};
		$ref_field = ($fieldname eq "new_password") ? $input_fields{"password"} : $input_fields{$fieldname};
		$value = $server_xml_data->{$fieldname};
		$data_type = $ref_field->{"data_type"};
		$title = $ref_field->{"title"};
		$modified = 0;
		print "Current value for $title = $value\n";
		while ( 1 ) {
			print "Enter value for $title : ";
			if ( $data_type eq "password" ) {
				$value = read_password("");
				print "\n";
			} # IF
			else {
				$value = <STDIN>;
			} # ELSE
			chomp $value;
			if ( $value eq "" ) {
				last;
			} # IF
			if ( $data_type eq "int" && $value =~ m/\D/ ) {
				print "Non numeric characters specified for $ref_field->{'title'} , try again\n";
				next;
			} # IF
			$modified = 1;
			last;
		} # WHILE
		if ( $modified ) {
			$count += 1;
			$input_fields{$fieldname}{"value"} = $value;
			if ( $data_type ne "int" ) {
				if ( $value =~ m/ / ) {
					$value =~ s/ /%20/g;
				} # IF
			} # IF
			$parms .= "&$fieldname=$value";
		} # IF
	} # FOREACH over input fields
	print "\n$count fields were modified\n";
	if ( $count ) {
		print "$parms\n";
		$status = send_request_to_server($parms);
		print "$server_xml_data->{'error_message'}\n";
		print "$server_xml_data->{'error_details'}\n";
	} # IF

	return 0;
} # end of moduser

######################################################################
#
# Function  : void_trans
#
# Purpose   : Process a "void" command
#
# Inputs    : (none)
#
# Output    : appropriate mesages
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
	my ( $status , $parms , $id );

	if ( 0 == scalar @ARGV ) {
		print "Usage : $script_name myname mypassword void transaction_id\n";
	} # if
	else {
		$id = $ARGV[0];
		$parms = "function=void&username=$username&password=$password&trans_id=$id";
		$status = send_request_to_server($parms);
		print "$server_xml_data->{'error_message'}\n";
		print "$server_xml_data->{'error_details'}\n";
	} # ELSE

	return 0;
} # end of void_trans

######################################################################
#
# Function  : MAIN
#
# Purpose   : Smart contracts client program
#
# Inputs    : @ARGV - optional arguments
#
# Output    : (none)
#
# Returns   : 0 --> success , non-zero --> failure
#
# Example   : smart.pl -d arg1 arg2
#
# Notes     : (none)
#
######################################################################

MAIN:
{
	my ( $status , $ref , @list );

	$script_name = basename($0);
	$status = getopts("hd",\%options);
	if ( $options{"h"} ) {
		display_pod_help($0);
		exit 0;
	} # IF
	unless ( $status && 2 < scalar @ARGV ) {
		die("Usage : $0 [-dh] username password function [optional parameters]\n");
	} # UNLESS

	$username = shift @ARGV;
	$password = shift @ARGV;
	$function = lc shift @ARGV;
	$ref = $functions{$function};
	if ( defined $ref ) {
		@list = @$ref;
		$list[0]->();
	} # IF
	else {
		die("'$function' is not a valid function\n");
	} # ELSE

	exit 0;
} # end of MAIN
__END__
=head1 NAME

smart.pl - Smart contracts client program

=head1 SYNOPSIS

smart.pl [-hd]

=head1 DESCRIPTION

Smart contracts client program

=head1 PARAMETERS

  (none)

=head1 OPTIONS

  -h - produce this summary
  -d - activate debugging mode

=head1 EXAMPLES

smart.pl

=head1 EXIT STATUS

 0 - successful completion
 nonzero - an error occurred

=head1 AUTHOR

Barry Kimelman

=cut
