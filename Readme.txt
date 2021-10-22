bcrypt==3.2.0
cffi==1.14.6
click==8.0.1
Flask==2.0.1
flask-swagger-ui==3.36.0
gitdb==4.0.7
GitPython==3.1.24
itsdangerous==2.0.1
Jinja2==3.0.1
MarkupSafe==2.0.1
psycopg2-binary==2.9.1
pycparser==2.20
redis==3.5.3
six==1.16.0
smmap==4.0.0
typing-extensions==3.10.0.2
Werkzeug==2.0.1


Server: http://23.88.52.139:5006

Swagger: http://23.88.52.139:5006/swagger

DB diagram: https://drawsql.app/myowncompany/diagrams/cto

Done:
	endpoints:
		/users:
			[GET] - get the short user_info (one/all, active/inactive)
			[POST] - register a new user
			[PUT] - change the user_info
			[DELETE] - delete the user by itsels (WARNING! ON DELETE CASCADE! (suicide :(

		/users/user_info
			[POST] - get the full user_info 
			
		/users/login:
			[POST]

		/users/activate:
			[POST] - mark the user as active
			
		/users/deactivate:
			[POST] - mark the user as inactive
			
		/users/vehicle:
			*[GET] - request a user's vehicle  			- not implemented (the info is provided in user_info. there will be another endpoint for managers)
			[POST] - create new user vehicle
			[PUT] - change a user's vehicle
			[DELETE] - delete a user's vehicle
			
		/storage_orders:
			*[GET] - request the storage_order 			- not implemented (the info is provided in user_info. there will be another endpoint for managers)
			[POST] - create new storage_order
			*[PUT] - change the storage_order			- closed. on maintenance
			[DELETE] - delete the storage_order
			
		/warehouse:
			[GET] - available storage
			
		/tire_service_order:
			*[GET] - request a user tire_service_order 	- not implemented (the info is provided in user_info. there will be another endpoint for managers)
			[POST] - create new user's tire_service_order
			*[PUT] - change a user's tire_service_order	- closed. on maintenance
			[DELETE] - delete a user's tire_service_order
			
		/tire_service_order/task:
			*[GET] - request the task 					- not implemented (the info is provided in user_info. there will be another endpoint for managers)
			*[POST] - create new task					- the tasks were created when creating the service order
			*[PUT] - change the task 					- not implemented (the user can delete or add tasks in the tire service order. only the manager can change workers)
			*[DELETE] - delete the task					- closed. on maintenance
		
	block-diagram:
*		/reg
d		/user_info
*		/new_storage_order
*		/login

	swagger:
		/users/activate
		/users/deactivate
		/users/login
		/users
		/users/user_info		
		/warehouse
		/vehicle
		/storage_order						
		/tire_service_order		
	
ToDo Dmitrii:

				- add a state vehicle number column to the user_vehicle table and in the output info in the user_info and [PUT] service order insetead of user_vehicle_id
				- validate required fields (not filleld is not working) test: False, True, '   ' (spaces)

		- user_vehicle_id in storage_order [PUT]?
	
	In progress: 
		- swagger
	
	- vehicle.name in /vehicle	[POST] - ok, but in [PUT]?	
    - 401 status code when the email or token does not exist?

	- drop the pass column from the users table?

	- the user can create two tire_service_orders for the same vehicle on the same date and time 
	- schedule (for workers)
	
	- staff: add other working professions
	- distribution of workers by type of work

	- admin:
	    - can change the managers in the tire_service_order
	    - can change the worker in the list_of_works
	    - can restore the user's password
		- generate reports:
		    - staff: all/available/unavailable (by position or all)
		    - costs: all/storage_orders/tire_service_oreders
		    - costs: on staff
	
	- swagger
	- design
	- requirements
	- frontend
	- testing:
		- checklists
*		- bug report google form
*		- improvements google form

ToDo Azat: 
        - design
        - front

DrawSQL DB:
	table Payment (payment_id, user_id, card_number, exp_date, owner_name, cvv_cvc)
	
DISCLAIMER:
Условности:
	Сервис работает 7 дней в неделю, так же и все работники.
	Рабочее время - 08:00 - 20:00
	Перерыв между заказами - 10 минут
	Все виды работ выполняются рабочими (дополнительные должности и виды работ планируются к реализации позже)
	Планируемое время окончания работ не может превышать 20:15
	При создании заказа на хранение не учитывается время - только дата (при пересечении времени подразумевается использование полки другого размера, или еще чего.. :)
	Ценообразование заказов и продолжительность работ взяты с потолка :)
	Назначение менеджеров: в первую очередь - рандомный менеджер без заказов; во вторую очередь - рандомный менеджер с наименьшим количеством заказов
	Назначение работяг: рандомный работяга, не занятый в необходимый промежуток времени
	Возможности изменения заказов не реализованы (пока?)
	Не рализована логика размещения шин на складе на полке большего размера при пересечении дат.

user_authorization checks: 	
	if email does not exist in the DB: return "The user does not exist. Please, register" and redirect to /reg
		if the token does not exist in redis db: The token is invalid, please log in

make sure that all the required fields are filled in

		
In memories:
	- the name of the availabe column in the warehouse has been changed to active - need to be tested
	- the size_id column in the storage_orders has been deleted - need to be tested
	- the st_ord_cost in the storage_orders has been renamed to storage_order_cost
	- the st_ord_id in the storage_orders has been renamed to storage_order_id
	- the u_veh_id in the user_vehicle has been renamed to user_vehicle_id
	- the u_veh_id in the tire_service_order has been renamed to user_vehicle_id
	- the serv_order__id in the tire_service_order has been renamed to service_order_id
	- the service_order_date in the tire_service_order has been renamed to start_datetime
	- the availabe in the staff has been renamed to active
	- the availabe in the managers has been renamed to active

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
			salt
			hash_password

	if email exists in the DB: 400 - note
	else: 
		add new user to the DB and return info from the DB with user_id


/users [GET]
	input:
			user_id				- optional	- type: int
			active				- optional  - format: 'yes', 'no', blank. Сase insensitive
	output:
			user_id				- type: int
			f_name				
			l_name
			email
			phone
	
	if there is a user_id in params: output info about this user
		if there is no params: output info about all users
			if the active parameter is 'yes' - output info about active user(s) only
			if the active parameter is 'no' - output info about inactive user(s) only
			if the active parameter is blank or something except 'yes' or 'no' - output info about all users
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
			start_date			- required - format - YYYY-MM-DD
			stop_date			- required - format - YYYY-MM-DD
			size_name			- optional
			user_vehicle_id		- optional
	
	output:
			storage_order_cost
			start_date
			stop_date
			shelf_id
			storage_order_id

	user_authorization
		the user can specify either the size_name or the user_vehicle_id
			if both size_name and user_vehicle_id are specified, the size_name is ignored

	shelf_id selection:
		- min shelf_id, that have no storage_order and matches on size_id needed
		- min shelf_id with the dates, that do not cross others

				
/storage_orders [PUT]	=========================================== ON MAINTENANCE ===============================================			
	input:
			storage_order_id 			- required
			email				- required
			token				- required
			start_date			- optional
			stop_date			- optional
			storage_order_cost	- optional
			size_id				- optional
			
	output:
			storage_order_id
			start_date
			stop_date
			size_id
			storage_order_cost
			shelf_id
	
	user_authorization
		if the provided dates are invalid: note
			if the optional data is None: take the data needed from DB
				if size_id is need to be changed make sure that the warehouse has an available shelf

				
/vehicle [POST]
	input:
			email				-required
			token				-required
			vehicle_name		-required
			size_name			-required
	
	output:
			user_vehicle_id
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
			phone               - optional

	output:
			user_id
			old_first_name
			new_first_name
			old_last_name
			new_last_name
			old_email
			new_email
			old_phone
			new_phone
	
	user_authorization
        if all optional data is None OR the new data is equal to the DB data: nothing needs to be changed
        if some optional data is None: take the data needed from DB
        if the email has been changed - the user must log in again
        if the new_email is already in the DB: 400 - email exists
					
/users/user [DELETE]
	input:
			email				- required
			token				- required
			ARE_YOU_SURE?		- required
			admin				- required - admin password
			
	output:
			sad message
			
	user_authorization
			if the "ARE_YOU_SURE?" value is not 'True': return a funny message
			
/users/deactivate [POST]
	input:	
			email				- required
			token				- required
			ARE_YOU_SURE?		- required		- format: 'True' for deactivate
	
	output:
			confirmaion message
			
	user_authorization
		if the user has already been deactivated: return a message
			if the "ARE_YOU_SURE?" value is not 'True': return a funny message
				if the process was completed successfully - remove the user's token from redis db
				
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
			user_vehicle_id
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
			size_name			- optional
			availabe only		- optional
	output:
			shelf_id
			size_id
			size_name
			availabe
			
	if there is a size_name in params: show shelf(s) for this size_name
		if there is no size_name in params: show shelf(s) for all size_name
			if there is a availabe only 'yes' in params: show only free shelf(s) for this size_name
				if there is a availabe only 'no' in params: show only occupied shelf(s) for this size_name

/tire_service_order [POST] ========================================== NEEDS UPDATING ==================================================
	input:
			email							- required
			token							- required
			order_date						- required
			user_vehicle_id	    			- required
			order_type						- required
			numbers_of_wheels				- required
			removing_installing_wheels		- required
			tubeless						- required
			balancing						- required
			wheel_alignment					- required

	
	output:
			service_order_id
			order datetime
			estimated service duration
			estimated end of service datetime
			service order cost
			manager:
				manager_id
				manager name
				manager_email
				manager_phone
			tasks:
				task_name
				task_cost
			worker:
				worker_id
				worker name
			
	user_authorization
		if it is not user's vehicle: - 403
		if the order date is before today - 400
		


/tire_service_order [PUT] =========================================== ON MAINTENANCE ===============================================
    input:
			email				- required
			token				- required
			service_order_id	- required
			new order date          - optional
			other user vehicle id   - optional

	output:
			user_id
			service_order_id
			old order date
			new order date
			old user vehicle id
			new user vehicle id
			
	user_authorization
		if it is not user's order: :)
		if it is not user's other vehicle: :)
		if the new order date is before today
		
					
/tire_service_order [DELETE]
	input:
			email				- required
			token				- required
			service_order_id	- required
			
	output:
			confirmation message
			
	user_authorization
		if it is not user's order: :)
		if the manager's load becomes less than 5 when the order is deleted, mark it as available
		delete the tasks on delete tire_service_order - DB settings ON DELETE CASCADE


/tire_service_order/task [POST] =========================================== ON MAINTENANCE ===============================================
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
				
/tire_service_order/task [DELETE] =========================================== ON MAINTENANCE ===============================================
	input:
			email				- required
			token				- required
			service_order_id	- required
			task_number			- optional
			
	output:
			list of works OR confirmaion message
	
	user_authorization
		if it is not user's order: :)
			if numbers_of_tasks is none or not isdigit: return warning message
				
