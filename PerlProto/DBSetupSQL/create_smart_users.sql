/*********************************************************************/
/*                                                                   */
/* File      : create_smart_users.sql                                */
/*                                                                   */
/* Author    : Barry Kimelman                                        */
/*                                                                   */
/* Created   : September 25, 2019                                    */
/*                                                                   */
/* Purpose   : Create smart contract users table                     */
/*                                                                   */
/* Notes     : (none)                                                */
/*                                                                   */
/*********************************************************************/

create table smart_users (
	id				int not null auto_increment,
	mod_date		date not null, /* date of creation or modification */
	username		varchar(40) not null,
	password		varbinary(4096) not null, /* use AES encryption */
	first_name		varchar(40) not null,
	last_name		varchar(40) not null,
	email			varchar(80) not null,
	phone			varchar(40) not null,
	priv_level		int not null, /* 0 = admin */
	balance1		int not null, /* initial balance in pennies */
	balance			int not null, /* current balance in pennies */
	status			enum('active','expired') not null,
	comment			varchar(100),
	primary key (id)
);

CREATE UNIQUE INDEX USERNAME_INDEX ON smart_users (username);
