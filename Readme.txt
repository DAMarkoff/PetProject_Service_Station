click==8.0.1
Flask==2.0.1
flask-swagger-ui==3.36.0
itsdangerous==2.0.1
Jinja2==3.0.1
MarkupSafe==2.0.1
psycopg2-binary==2.9.1
redis==3.5.3
Werkzeug==2.0.1

Server: http://23.88.52.139:5006

Swagger: http://23.88.52.139:5006/swagger

DB diagram: https://drawsql.app/myowncompany/diagrams/cto

Done:
	endpoints:
		/users:
			GET - get the short user_info (one/all)
			POST - register a new user
			PUT - change the user_info
			DELETE - delete the user by itsels (WARNING! ON DELETE CASCADE! (suicide :(

		/users/user_info
			POST - get the full user_info 
			(include: short user_info; user's vehicle; user's storage_orders; user's tire_service_orders with tasks and costs)
			
		/users/login:
			POST

		/users/activate:
			POST - mark the user as active
			
		/users/deactivate:
			POST - mark the user as inactive
			
		/users/vehicle:
			*GET - request a user's vehicle  			- not implemented
			POST - create new user vehicle
			PUT - change a user's vehicle
			DELETE - delete a user's vehicle
			
		/storage_orders:
			*GET - request the storage_order 			- not implemented
			POST - create new storage_order
			PUT - change the storage_order
			DELETE - delete the storage_order
			
		/warehouse:
			GET - available storage
			
		/tire_service_order:
			*GET - request a user tire_service_order 	- not implemented
			POST - create new user's tire_service_order
			*PUT - change a user's tire_service_order	- not implemented
			DELETE - delete a user's tire_service_order
			
		/tire_service_order/task:
			*GET - request the task 					- not implemented
			POST - create new task
			*PUT - change the task 						- not implemented
			*DELETE - delete the task 					- not implemented
		
	block-diagram:
*		/reg
d		/user_info
*		/new_storage_order
*		/login

	swagger:
		/login
		/all
		/available_storage
		/reg
	
ToDo: 
	- move the Pex.txt cobtent to the README.md
	- warehouse:
		- create a summary JSON report on demand
		- include an info with unavailabe storage on demand
	- store the user's passwords in hash
	- the user can delete a tire_service_order with an expired date
*	- simple return after the DB connection error - 503
	- the user can create two tire_service_orders for the same vehicle on the same date and time 
	- schedule (for workers)
	- add to list_of_works how to choose a worker 
	- new storage order dates validate (start before today)
	- update the token's TTL in the redis db after each user action
	
	- staff: add other working professions
	- distribution of workers by type of work

	- /change_tire_service_order
	- /add_task_to_list_of_works
	- /change_list_of_works
	- /delete_list_of_works
	- /create_subscription
	- /change_subscription
	- /delete_subscription
	
	- swagger

DrawSQL DB:
	table Payment (payment_id, user_id, card_number, exp_date, owner_name, cvv_cvc)
	
DISCLAIMER:
user_authorization checks: 	
	if email does not exist in the DB: return "The user does not exist. Please, register" and redirect to /reg
		if the token does not exist in redis db: redirect to /login

/users/login [POST]
	input:  
			email				- required
			password			- required
		
	output: 
			hello_message
			email
			token
			user_id

	if email does not exist in DB: 400 - note
		if pass does not valid: 401 - note
			if token exists in the redis db: set new ex time and return the token
			else: 
				generate new token, add to the redis db and return it


/users [POST]
	input: 
			f_name				- required
			l_name				- required
			email				- required
			phone				- required
			password			- required
		   
	output: 
			user_id
			f_name
			l_name
			email
			phone
			passw
			
	if email exists in the DB: 400 - note
	else: 
		add new user to the DB and return info from the DB with user_id


/all [GET]
	input:
			user_id				- optional
	output:
			user_id
			f_name			
			l_name
			email
			phone
			password
	
	if there is a user_id in params: output info about this user
		if there is no params: output info about all users
			if there are no users in the DB: note


/users/user_info [POST]
	input: 
			email				- required
			token				- required

	output:
			user_id
			f_name
			l_name
			email
			phone
			passw
	
	user_authorization
			return info

	
/storage_orders [POST]
	input:
			token				- required
			email				- required
			start_date			- required
			stop_date			- required
			size_name			- required
	
	output:
			email
			start_date
			stop_date
			size_id
			shelf_id
			st_ord_id

	user_authorization
			if there is no available shelf of the size needed in the warehouse: note		
				add in the "storage_order" base info about the storage order
				update in the "warehouse" base availability of the occupied storage place

				
/storage_orders [PUT]				
	input:
			st_ord_id 			- required
			email				- required
			token				- required
			start_date			- optional
			stop_date			- optional
			st_ord_cost			- optional
			size_id				- optional
			
	output:
			st_ord_id
			start_date
			stop_date
			size_id
			st_ord_cost
			shelf_id
	
	user_authorization
			if the provided dates are invalid: note
				if the optional data is None: take the data needed from DB
				if size_id is need to be changed make sure that the warehouse has an availabe shelf

				
/vehicle [POST]
	input:
			email				-required
			token				-required
			vehicle_name		-required
			size_name			-required
	
	output:
			u_veh_id
			vehicle_name
			size_name
			
	user_authorization
			if the vehcile type or tire size is not specified in the DB: note 
				add the date in to the DB
				
/users/user [PUT]				
	input:
			email				- required
			token				- required
			f_name				- optional
			l_name				- optional
			new_email			- optional
			password			- optional

			
	output:
			user_id
			f_name
			l_name
			email
			phone
			password
	
	user_authorization
			if all optional data is None OR the new data is equal to the DB data: nothing needs to be changed
				if some optional data is None: take the data needed from DB
					if the password and/or email have been changed - the user must log in again
					
/users/user [POST]
	input:
			email				- required
			token				- required
			ARE_YOU_SURE?		- required
			
	output:
			sad message
			
	user_authorization
			if the "ARE_YOU_SURE?" value is not 'True': return a funny message
			
/users/deactivate [POST]
	input:	
			email				- required
			token				- required
			ARE_YOU_SURE?		- required
	
	output:
			confirmaion message
			
	user_authorization
			if the user has already been deactivated: return a message
				if the "ARE_YOU_SURE?" value is not 'True': return a funny message
				
/users/activate [POST]
	input:	
			email				- required
			admin_password		- required
	
	output:
			confirmaion message
			
	the email must exist, admin_password is 'admin'
			
/vehicle [DELETE]
	input:
			email				- required
			token				- required
			user_vehicle_id		- required
	
	output:
			confirmaion message

	user_authorization
			if it is not user's vehicle: Call the police!!! :)

/storage_orders [DELETE]	
	input:
			email				- required
			token				- required
			storage_order_id	- required
	
	output:
			confirmaion message

	user_authorization
			if it is not user's storage order: :)
		
/vehicle [PUT]
	input:
			email				- required
			token				- required
			user_vehicle_id		- required
			new_vehicle_name	- optional
			new_size_name		- optional
			
	output:
			u_veh_id
			old_vehicle_name
			new_vehicle_name
			old_size_name
			new_size_name
			
	user_authorization
			if it is not user's vehicle: Call the police!!! :)
				if all optional data is None OR the new data is equal to the DB data: nothing needs to be changed
					if some optional data is None: take the data needed from DB

/warehouse [GET]
	input:
			size_id				- optional
	output:
			shelf_id
			size_id
			size_name
			
	if there is a size_id in params: shoe free shelf(s) for this size_id
		if there is no params: show info about all free shelf(s)

/tire_service_order [POST]
	input:
			email				- required
			token				- required
			order_date			- required
			user_vehicle_id_id	- required

	
	output:
			service_order_id
			date
			worker_id
			worker_first_name
			worker_last_name
			worker_phone
			worker_email
			
	user_authorization
			if it is not user's vehicle: :)
				max load per one manager - 5
					
/tire_service_order [DELETE}
	input:
			email				- required
			token				- required
			service_order_id	- required
			
	output:
			confirmaion message
			
	user_authorization
			if it is not user's order: :)
				if manager's load becomes less than 5, then mark the manager as available
				
			
/tire_service_order/task [POST]
	input:
			email				- required
			token				- required
			service_order_id	- required
			task_name			- required
			numbers_of_tasks	- optional
			
	output:
			confirmaion message
	
	user_authorization
			if it is not user's order: :)
				if numbers_of_tasks is none or not isdigit: return warning message
					