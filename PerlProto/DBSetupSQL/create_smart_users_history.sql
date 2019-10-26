/*********************************************************************/
/*                                                                   */
/* File      : create_smart_users_history.sql                        */
/*                                                                   */
/* Author    : Barry Kimelman                                        */
/*                                                                   */
/* Created   : September 25, 2019                                    */
/*                                                                   */
/* Purpose   : Create smart contract users history table             */
/*                                                                   */
/* Notes     : This table records all transactions that affect the   */
/*             balance of a user.                                    */
/*                                                                   */
/*********************************************************************/

create table smart_users_history (
	id				int not null auto_increment,
	mod_date		datetime not null, /* date of creation or modification */
	user1			int not null, /* user_id of user issuing command */
	user1_balance	int not null, /* user1 balance after operation */
	user2			int not null, /* user_id of affected user */
	user2_balance	int not null, /* user2 balance after operation */
	operation		varchar(80) not null, /* operation (e.g. send) */
	status			enum('active','voided') not null,
	amount			int not null,  /* amount of currency in transaction */
	primary key (id)
);
