insert into smart_users
( mod_date , username , password , first_name , last_name , email , phone , priv_level , balance1 , balance , status )
values
( CURDATE() , "luke" , aes_encrypt('sierra','pizza') , "luke" , "skywalker" , "luke@force.com" , "204-2222222" , 1 , 2000000 , 2000000 , "active" );
