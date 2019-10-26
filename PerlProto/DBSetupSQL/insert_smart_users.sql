/*********************************************************************
*
* File      : insert_smart_users.sql
*
* Author    : Barry Kimelman
*
* Created   : September 25, 2019
*
* Purpose   : Insert records into the smart users table
*
* Notes     : (none)
*
*********************************************************************/

insert into smart_users
( mod_date , username , password , first_name , last_name , email , phone , priv_level , balance1 , balance , status )
values
( CURDATE() , "barry" , aes_encrypt("cookies","pizza") , "barry" , "kimelman" , "bk@stuff.com" , "204-1234567" , 0 , 2000000 , 2000000 , "active" );

insert into smart_users
( mod_date , username , password , first_name , last_name , email , phone , priv_level , balance1 , balance , status )
values
( CURDATE() , "doug" , aes_encrypt("sierra","pizza") , "doug" , "kimelman" , "dk@stuff.com" , "204-2222222" , 1 , 2000000 , 2000000 , "active" );
