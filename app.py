import fpdf as fpdf
import xlwt
from flask import Flask, render_template, session, redirect, url_for, request, flash, make_response, Response
from flask_mysqldb import MySQL #imported mysql for database
from passlib.handlers.sha2_crypt import sha256_crypt
from wtforms import Form,StringField,TextAreaField,IntegerField,PasswordField,validators,SelectMultipleField,SelectField #used wtforms to create forms
from functools import wraps
import os
from flask import send_file

app = Flask(__name__)
app.secret_key = 'super secret key'

#configuration of MySQL
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = ""   #ENTER THE PASSWORD OF THE MYSQL HERE
app.config['MYSQL_DB'] = "bank"
app.config['MYSQL_CURSORCLASS'] = "DictCursor"

#initialized Mysql
mysql = MySQL(app)

#To register the executive and cashier users.
#--------------------------------------------------------------------------------------------------
class Sample_register(Form):
    username  = StringField('User Name', [validators.InputRequired()])
    password = PasswordField('Password', [validators.Length(min=10),validators.InputRequired(),validators.Regexp(regex='((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[\W]).{10,})',message="Require One Special Character,One Capital letter,One Small letter and one number")])
    position = SelectField('Position*', choices=[('executive', 'executive'), ('cashier', 'cashier')])


@app.route('/sample_register',methods=['POST','GET'])
def sample_register():
    form = Sample_register(request.form)
    if request.method == 'POST' and form.validate() == True:
        username = form.username.data

        password = sha256_crypt.encrypt(str(form.password.data))

        position = form.position.data

        cur = mysql.connection.cursor()
        # get ssnid by customer in db
        result = cur.execute("select * from users where position= %s", [position])
        cur.close()
        # if the result is fetched then redirect with message as ssnid already used
        if result > 0:
            flash("Account with this position already exists,If more than 1 account is required then contact Manager",'danger')
            return render_template("sample_registration.html", form=form)
        else:
            cur = mysql.connection.cursor()
            cur.execute("insert into users(username,password,position) VALUES(%s,%s,%s)",(username,password,position))
            mysql.connection.commit()
            cur.close()
            flash("Successfully User Registered",'success')
            return redirect('/')
    return render_template("sample_registration.html", form=form)


#--------------------------------------------------------------------------------------------------
#Home Login page for executive/cashier
@app.route('/',methods=['GET','POST'])
def home():
    if request.method == 'POST':
        #Get form fields entered in login form
        username = request.form['username']
        password_candidate = request.form['password']

        #Create cursor for sql connection
        cur = mysql.connection.cursor()

        #get user by username in db
        result = cur.execute("select * from users where username= %s",[username])

        #if the result is fetched then take the password from db
        if result>0:
            #Get Stored Hash
            data = cur.fetchone() #fetch the data in db
            password = data['password'] #get the password

            #compare passwords
            if sha256_crypt.verify(password_candidate,password): #check the password from login form and database
                #Passed
                session['logged_in']=True  #session started
                session['username'] = username
                if data['position']=='executive':
                    flash('You are now logged in','success')   #flash the message on the screen
                    return redirect(url_for('executive'))      #redirect to executive url if successfull
                elif data['position']=='cashier':
                    flash('You are now logged in','success')
                    return redirect(url_for('cashier'))      #redirect to cashier url if successfull
            else:
                error = 'Invalid Login Password'           #if password doesn't match then show this error
                return render_template('home.html',error=error)
            #CLose Connection
            cur.close()
        else:          #if no result is fetched, it means there is no such username in db
            error = 'Username Not Found'  #display this error
            return render_template('home.html',error=error)
    return render_template('home.html')


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('home'))
    return wrap

#--------------------------------------------------------------------------------------------------

#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()  #clear entire session and redirect back to home url by redirect
    flash('You are Logged out','success')
    return redirect(url_for('home'))

#Account Executive Page
@app.route('/executive')
@is_logged_in
def executive():
    return render_template('executive_index.html')

#To Add Customer Registration Form
class RegisterForm(Form):
    cust_ssnid = IntegerField('customer SSN Id', [validators.NumberRange(min=100000000, max=999999999)])
    cname = StringField('Customer Name*',[validators.Length(min=3,max=25)])
    age = IntegerField('Age*')
    address = StringField('Address*',[validators.Length(min=3)])
    state = SelectField('State*', choices=[('Andhra Pradesh','Andhra Pradesh'),('Assam','Assam'),('Bihar','Bihar'),('Chhattisgarh','Chhattisgarh'),('Goa','Goa'),('Gujarat','Gujarat'),('Haryana','Haryana'),('Himachal Pradesh','Himachal Pradesh'),('Jammu and Kashmir','Jammu and Kashmir'),('Jharkhand','Jharkhand'),('Karnataka','Karnataka'),('Kerala','Kerala'),('Madya Pradesh','Madya Pradesh'),('Manipur','Manipur'),('Meghalaya','Meghalaya'),('Shillong','Shillong'),('Mizoram','Mizoram'),('Nagaland','Nagaland'),('orissa','orissa'),('Punjab','Punjab'),('Rajasthan','Rajasthan'),('Sikkim','Sikkim'),('Telagana','Telagana'),('Tripura','Tripura'),('Uttaranchal','Uttaranchal'),('Uttar Pradesh','Uttar Pradesh'),('West Bengal','West Bengal'),('Maharashtra', 'Maharashtra'),('Tamil Nadu', 'Tamil Nadu')])

#Add Customer Page
@app.route('/add_customer',methods=['GET','POST'])
@is_logged_in
def add_customer():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate(): #check the form is validated and method is post
        cust_ssnid = form.cust_ssnid.data #takes data from the form
        cname = form.cname.data
        age = int(request.form['age'])
        address = form.address.data
        state = form.state.data
        #created cursor for mysql connection
        cur = mysql.connection.cursor()

        #get ssnid by customer in db
        result = cur.execute("select * from customers where cust_ssnid= %s",[cust_ssnid])

        #if the result is fetched then redirect with message as ssnid already used
        if result>0:
            flash("SSNID Already Used Please Use Another",'danger')
            return redirect(url_for('add_customer'))
        #Else insert the data into Table
        status = "active"
        messages= "Customer Account is Created"
        cur.execute("INSERT INTO customers(cust_ssnid,cname,age,address,state,status,messages) VALUES(%s,%s,%s,%s,%s,%s,%s)",(cust_ssnid,cname,age,address,state,status,messages))

        #commit to db
        mysql.connection.commit()

        #close connection
        cur.close()

        flash("New Customer is Created",'success') #flash msg that customer record is created and redirect
        return redirect(url_for('executive'))
    return render_template('add_customer.html',form=form)

#Delete Customer View Page
@app.route('/del_customer',methods=['GET','POST'])
@is_logged_in
def del_customer():
    if request.method == "POST":
        cid= request.form['cid'] #takes the data from search form
        cust_ssnid = request.form['cust_ssnid'] #takes the data from search form
        #create cursor for connection
        cur = mysql.connection.cursor()
        #get the data from db
        data = cur.execute('select * from customers where cid = %s or cust_ssnid=%s',[cid,cust_ssnid])

        if data==1: #if data is present then render the page to del_customer along with all the data
            result = cur.fetchall()
            cur.close()
            return render_template('del_customer.html',result=result) # <- Here you jump away from whatever result you create
        elif data==2:
            error = 'Enter Only 1 Field'
            return render_template('search.html',error=error)
        else:     #Else display there is no such data in db
            error = "No such Customer data is present"
            return render_template('search.html',error=error)
    return render_template('search.html')

# Delete Customer From db
@app.route('/del_cust/<string:cid>', methods=['GET','POST']) #takes the cid from the del_customer html form
@is_logged_in
def del_cust(cid):
    # Create cursor
    cur = mysql.connection.cursor()
    # Execute
    res = cur.execute('select * from accounts where cid = %s',[cid])
    if res>0:
        cur.execute('Delete from transactions where cid = %s',[cid])
        cur.execute('Delete from accounts where cid = %s',[cid])
        cur.execute("DELETE FROM customers WHERE cid = %s", [cid])
        # Commit to DB
        mysql.connection.commit()
        #Close connection
        cur.close()
        flash('Customer Data Deleted', 'success')
        return redirect(url_for('executive'))
    else:
        cur.execute("DELETE FROM customers WHERE cid = %s", [cid])
        # Commit to DB
        mysql.connection.commit()
        #Close connection
        cur.close()
        flash('Customer Data Deleted', 'success')
        return redirect(url_for('executive'))

#To Update Customer Form
class UpdateForm(Form):
    cname = StringField('Customer New Name',[validators.Length(min=3,max=25)])
    age = IntegerField('New Age',[validators.Length(min=1,max=2)])
    address = StringField('New Address',[validators.Length(min=3)])

#Update Customer View Page
@app.route('/update_customer',methods=['GET','POST'])
@is_logged_in
def update_customer():
    form = UpdateForm(request.form)
    if request.method == 'POST':
        cid= request.form['cid'] #takes the data from search form
        cust_ssnid = request.form['cust_ssnid']
        #create cursor
        cur = mysql.connection.cursor()
        data = cur.execute('select * from customers where cid = %s or cust_ssnid=%s',[cid,cust_ssnid])
        if data==1:
            result = cur.fetchall()
            cur.close()
            return render_template('update_customer.html',form=form,result=result)
        elif data==2:
            error = 'Enter Only 1 Field'
            return render_template('search.html',error=error)
        else:
            error = "No such Customer data is present"
            return render_template('search.html',error=error,form=form)
    return render_template('search.html',form=form)

#Updated Customer
@app.route('/update_cust/<string:cid>',methods=['GET','POST']) #takes cid from update_customer html form
@is_logged_in
def update_cust(cid):
    form = UpdateForm(request.form)
    if request.method == 'POST':
        cname = request.form['cname'] #takes the data from update_customer form
        age = request.form['age']
        address = request.form['address']
        cur = mysql.connection.cursor()
        messages = "Customer Account is Updated"
        # Execute Update Command
        res = cur.execute("Update customers set cname = %s,age = %s,address = %s , messages = %s WHERE cid = %s", [cname,age,address,messages,cid])
        # Commit to DB
        mysql.connection.commit()
        #Close connection
        cur.close()
        flash('Customer Data Updated', 'success')
        return redirect(url_for('executive'))

#----------------------------------------------------------------------------------------------
#Account Creation Form
class AccountForm(Form):
    cust_ssnid = StringField('Customer ID*',[validators.Length(min=1,max=50)]) #validators used to validate the wtform
    acc_type = SelectField('Account Type*', choices=[('S','Savings Account'),('C','Current Account')])
    deposit_amt = IntegerField('Deposit Amount*',[validators.NumberRange(min=1000, max=999999999)])


#Add Account Page
@app.route('/add_account',methods=['GET','POST'])
@is_logged_in
def add_account():
    form = AccountForm(request.form)
    if request.method == 'POST' and form.validate(): #check the form is validated and method is post
        cust_id = form.cust_ssnid.data #takes data from the form
        acc_type = form.acc_type.data
        deposit_amt = form.deposit_amt.data
        #created cursor for mysql connection
        cur = mysql.connection.cursor()
        #if the customer SSNID is not prezent then it will show an error
        res = cur.execute("select * from customers where cid=%s", [cust_id])
        if res > 0 :
            cur.close()
            cur = mysql.connection.cursor()
            res = cur.execute("select * from accounts where cid=%s and acctype=%s", [cust_id,acc_type])
            if res > 0 :
                cur.close()
                flash("Account Type Already Existed","danger")
                return render_template('add_account.html', form=form)
            else :

                status ="active"
                messages = "Account Created Successfully"

                cur = mysql.connection.cursor()

                cur.execute("INSERT INTO accounts(cid,acctype,balance,status,messages) VALUES(%s,%s,%s,%s,%s)",(cust_id,acc_type,deposit_amt,status,messages))

                mysql.connection.commit()

                cur.close()

                flash("Account Inserted", "success")
                return redirect('executive')
        else :
            flash("Customer Does not Exists", "danger")
            return render_template('add_account.html', form=form)
    elif request.method == 'GET':
        return render_template('add_account.html', form=form)
    return render_template('add_account.html',form=form)


class DeleteAccount(Form):
    CUSTOMER_ID   = StringField('CUSTOMER ID',[validators.Length(min=1,max=9)])
    Account_Type = SelectField('Account Type*', choices=[('S','Savings Account'),('C','Current Account')])

#Delete account page
@app.route('/del_account', methods=['POST', 'GET'])
@is_logged_in
def delete_account():
    form = DeleteAccount(request.form)
    if request.method == "POST":
        CUSTOMER_ID = form.CUSTOMER_ID.data
        Account_Type = form.Account_Type.data
        #create cursor for connection
        cur = mysql.connection.cursor()
        if (CUSTOMER_ID and Account_Type):
            data1=cur.execute("select * FROM accounts WHERE cid = %s", [CUSTOMER_ID])
            if (data1 > 0):
                result1 = cur.fetchall()
                cur.close()

                cur = mysql.connection.cursor()
                data2=cur.execute("select * from accounts WHERE acctype = %s", [Account_Type])
                if(data2 > 0):
                    cur.close()

                    cur = mysql.connection.cursor()
                    cur.execute("delete from transactions where cid = %s", [CUSTOMER_ID])
                    cur.execute("delete from accounts WHERE acctype = %s and cid = %s", [ Account_Type , CUSTOMER_ID ])
                    mysql.connection.commit()
                    cur.close()
                    flash('Account Deleted', 'success')
                    return redirect('/executive')

                else :
                    flash('Account Type Does not Exist', 'danger')
                    return render_template('del_account.html', form=form)
            else:
                flash('Account ID Doesnot Exist', 'danger')
                return render_template('del_account.html', form=form)

        else :
            flash("Type Both Option",'danger')
            return render_template('del_account.html',form=form)

    elif request.method == "GET":
            return render_template('del_account.html', form=form)

    return render_template('del_account.html',form=form)

#---------------------------------------------------------------------------------------------------------
#To view Customer Details
@app.route('/customer_view')
@is_logged_in
def customer_view():
    return render_template('customer_view.html')


#------------------------------------------------------------------------------------------------------------------------
#To View Customer Detail Status
@app.route('/customer_status',methods=['POST','GET'])
@is_logged_in
def customer_status():
    if request.method=='POST':
        cid = request.form['cid']
        cur = mysql.connection.cursor()
        data = cur.execute('select * from customers where cid = %s',[cid])
        if data > 0:
            result = cur.fetchall()
            cur.close()
            return render_template('customer_status.html', result=result)
        else :
            return render_template('customer_status.html')
    limit=10
    cur = mysql.connection.cursor()
    data1 = cur.execute('select * from customers order by timestamp desc limit %s',[limit])
    if data1 > 0:
        result1 = cur.fetchall()
        cur.close()
        return render_template('customer_status.html' , result = result1)
    else :
        flash("No Customer Created Till Now",'danger')
        return render_template('customer_status.html')

#--------------------------------------------------------------------------------------------------------------------
#To View Specific Customer Details
@app.route('/customer_status_view/<string:cid>',methods=['GET','POST'])
@is_logged_in
def customer_status_view(cid):
    if request.method == "POST":
        cur = mysql.connection.cursor()
        data = cur.execute('select * from customers where cid = %s',[cid])
        if data > 0:
            result = cur.fetchall()
            return render_template('customer_status_view.html',result=result)


#----------------------------------------------------------------------------------------------------------------
#To View Account Status
@app.route('/account_status',methods=["POST","GET"])
@is_logged_in
def account_status():
    if request.method == 'POST':
        accid = request.form['accid']
        cur = mysql.connection.cursor()
        data = cur.execute('select * from accounts where accid = %s', [accid])
        if data > 0:
            result = cur.fetchall()
            cur.close()
            return render_template('account_status.html', result=result)
    limit = 20
    cur = mysql.connection.cursor()
    data1 = cur.execute('select * from accounts order by udate desc limit %s',[limit])
    if data1 > 0:
        result1 = cur.fetchall()
        cur.close()
        return render_template('account_status.html' , result = result1)
    else :
        flash("No Account Created Till Now",'danger')
        return render_template('account_status.html')

#--------------------------------------------------------------------------------------------------------------------
#Cashier Index Page
@app.route('/cashier')
@is_logged_in
def cashier():
    return render_template('cashier_index.html')

#-----------------------------------------------------------------------------------------------------------
#Cashier Deposit Page
@app.route('/cashier_deposit_status',methods=["POST","GET"])
@is_logged_in
def cashier_deposit_status():
    if request.method == "POST":
        accid=request.form['accid']
        cur = mysql.connection.cursor()
        data = cur.execute('select * from accounts where accid = %s',[accid])
        if data > 0:
            result=cur.fetchall()
            cur.close()
            return render_template('cashier_deposit_status.html', result=result)
        else:
            flash("No Such Account is present","danger")
            return render_template('cashier_deposit_status.html')

    elif request.method == "GET":
        cur = mysql.connection.cursor()
        data1 = cur.execute('select * from accounts')
        if data1 > 0:
            result1 = cur.fetchall()
            cur.close()
            return render_template('cashier_deposit_status.html', result=result1)
        else:
            flash("No Customer Created Till Now", 'danger')
            return render_template('cashier_deposit_status.html')
    return "working"

@app.route('/account_deposit_view/<string:accid>',methods=['GET','POST'])
@is_logged_in
def account_deposit_view(accid):
    if request.method == "POST":
        cur = mysql.connection.cursor()
        data = cur.execute('select * from accounts where accid = %s',[accid])
        if data > 0:
            result = cur.fetchall()
            cur.close()
            return render_template('cashier_deposit.html',data=result)


@app.route('/account_succuess_view/<string:accid>',methods=['GET','POST'])
@is_logged_in
def account_success_view(accid):
    if request.method == 'POST':
        deposit = request.form['deposit']
        dvalue=str(deposit)
        if len(dvalue) < 10:
            cur = mysql.connection.cursor()
            data = cur.execute('select * from accounts where accid = %s', [accid])
            result = cur.fetchall()
            old_balance=result[0]['balance']
            cur.close()
            new_balance=int(old_balance) + int(dvalue)
            cur = mysql.connection.cursor()
            messages = "Latest : Money Deposited in this Account"
            cur.execute("Update accounts set balance = %s , messages = %s WHERE accid = %s",[new_balance, messages , accid])
            mysql.connection.commit()
            cur.close()

            cur = mysql.connection.cursor()
            stype = session['username']
            status = "Deposit"
            amount = int(dvalue)
            accid=accid
            cid=result[0]['cid']
            dtype=result[0]['acctype']
            cur.execute("INSERT INTO transactions(cid,accid,stype,dtype,status,amount) VALUES(%s,%s,%s,%s,%s,%s)", [cid,accid,stype,dtype,status,amount])
            mysql.connection.commit()
            cur.close()

            flash("SuccessFully Deposited in Your Account",'success')
            return redirect("/cashier")
        else:
            flash("Requires Manager Permission",'danger')
            return redirect("/cashier")


    return "working"
#--------------------------------------------------------------------------------------------------------------------
#withdrawal coding
@app.route('/cashier_withdrawal_status',methods=['GET','POST'])
@is_logged_in
def cashier_withdrawal_status():
    if request.method == "POST":
        accid = request.form['accid']
        cur = mysql.connection.cursor()
        data = cur.execute('select * from accounts where accid = %s', [accid])
        if data > 0:
            result = cur.fetchall()
            cur.close()
            return render_template('cashier_withdrawal_status.html', result=result)
        else:
            flash("No Such Account is present", "danger")
            return render_template('cashier_withdrawal_status.html')
    elif request.method == "GET":
        cur = mysql.connection.cursor()
        data1 = cur.execute('select * from accounts')
        if data1 > 0:
            result1 = cur.fetchall()
            cur.close()
            return render_template('cashier_withdrawal_status.html', result=result1)
        else:
            flash("No Customer Created Till Now", 'danger')
            return render_template('cashier_deposit_status.html')
    return "working"


@app.route('/account_withdrawal_view/<string:accid>',methods=['GET','POST'])
@is_logged_in
def account_withdrawal_view(accid):
    if request.method == "POST":
        cur = mysql.connection.cursor()
        data = cur.execute('select * from accounts where accid = %s',[accid])
        if data > 0:
            result = cur.fetchall()
            cur.close()
            return render_template('cashier_withdrawal.html',data=result)


@app.route('/accounts_succuess_view/<string:accid>',methods=['GET','POST'])
@is_logged_in
def accounts_success_view(accid):
    if request.method == 'POST':
        withdraw = request.form['withdraw']
        dvalue=str(withdraw)
        if len(dvalue) < 10:
            cur = mysql.connection.cursor()
            data = cur.execute('select * from accounts where accid = %s', [accid])
            result = cur.fetchall()
            old_balance=result[0]['balance']
            cur.close()
            new_balance=int(old_balance) - int(dvalue)
            if new_balance >= 1000 :
                messages = 'Latest : Money Withdrawed in this Account'
                cur = mysql.connection.cursor()
                cur.execute("Update accounts set balance = %s , messages = %s WHERE accid = %s", [new_balance,messages, accid])
                mysql.connection.commit()
                cur.close()

                cur = mysql.connection.cursor()
                dtype = session['username']
                status = "Withdrawal"
                amount = int(dvalue)
                accid = accid
                cid = result[0]['cid']
                stype = result[0]['acctype']
                cur.execute("INSERT INTO transactions(cid,accid,stype,dtype,status,amount) VALUES(%s,%s,%s,%s,%s,%s)",
                            [cid, accid, stype, dtype, status, amount])
                mysql.connection.commit()
                cur.close()

                flash("SuccessFully Withdrawal",'success')
                return redirect("/cashier")
            else:
                flash("Balance Should be Minimum 1000 in Account",'danger')
                return redirect("/cashier")


        else:
            flash("Requires Manager Permission",'danger')
            return redirect("/cashier")

    return "working"

#-------------------------------------------------------------------------------------

class TranscationForm(Form):
    source_account = SelectField('Source Account Type',choices=[('current', 'CURRENT'), ('saving', 'SAVING')])
    dest_account = SelectField('Destination Account Type', choices=[('current', 'CURRENT'), ('saving', 'SAVING')])
    tranf_amount = StringField('Amount to be Transferred',[validators.Length(min=1)])

#Cashier Transfer Page
#---------------------------------------------------------------------------------------------
@app.route('/cashier_transfer_status',methods=['GET','POST'])
@is_logged_in
def cashier_transfer_status():
    if request.method == "POST":
        accid = request.form['accid']
        cur = mysql.connection.cursor()
        data = cur.execute('select * from accounts where accid = %s', [accid])
        if data > 0:
            result = cur.fetchall()
            cur.close()
            return render_template('cashier_transfer_status.html', result=result)
        else:
            flash("No Such Account is present", "danger")
            return render_template('cashier_transfer_status.html')
    elif request.method == "GET":
        cur = mysql.connection.cursor()
        data1 = cur.execute('select * from accounts')
        if data1 > 0:
            result1 = cur.fetchall()
            cur.close()
            return render_template('cashier_transfer_status.html', result=result1)
        else:
            flash("No Customer Created Till Now", 'danger')
            return render_template('cashier_transfer_status.html')
    return "working"


@app.route('/account_transfer_view/<string:accid>' , methods=['POST','GET'])
@is_logged_in
def account_transfer_view(accid):
    cur = mysql.connection.cursor()
    data = cur.execute('select * from accounts where accid = %s', [accid])
    result = cur.fetchall()
    cur.close()
    if request.method == 'POST':
        return render_template('cashier_transfer.html',data=result)
    elif request.method == 'GET':
        return render_template('cashier_transfer.html', data=result)
    flash("Cannot Go Furthur",'danger')
    return redirect('/cashier')


@app.route('/accountt_succuess_view/<string:cid>',methods=['POST','GET'])
@is_logged_in
def accountt_success_view(cid):
    cur = mysql.connection.cursor()
    data = cur.execute('select * from accounts where cid = %s', [cid])
    result = cur.fetchall()
    cur.close()
    if request.method == 'POST':
        amount=request.form['transfer']
        source=request.form['sbtype']
        dest=request.form['dbtype']
        if source == dest :
            flash("Source and Destination Cannot be same Type",'danger')
            return render_template('cashier_index.html', data=result)
        else :
            cur = mysql.connection.cursor()
            data1 = cur.execute('select * from accounts where cid = %s and acctype = %s', [cid,source])
            result1 = cur.fetchall()
            cur.close()
            cur = mysql.connection.cursor()
            data2 = cur.execute('select * from accounts where cid = %s and acctype = %s', [cid, dest])
            result2 = cur.fetchall()
            cur.close()
            if(data1 > 0 and data2 >0):
                balance1=int(result1[0]['balance'])
                balance2 = int(result2[0]['balance'])
                if balance1-1000 < int(amount):
                    flash("Less Amount in Source Cannot Transfer as minimum 1000 should be there",'danger')
                    return redirect('/cashier')
                else:
                    sbal = balance1 - int(amount)
                    dbal = balance2 + int(amount)
                    cur = mysql.connection.cursor()
                    messages = "Latest : Money Withdrawed in this account"
                    cur.execute("Update accounts set balance = %s , messages = %s WHERE cid = %s and acctype=%s", [sbal,messages,cid,source])
                    mysql.connection.commit()
                    cur.close()
                    cur = mysql.connection.cursor()
                    messages = "Latest : Money Deposited in this account"
                    cur.execute("Update accounts set balance = %s , messages =  %s WHERE cid = %s and acctype=%s", [dbal,messages, cid, dest])
                    mysql.connection.commit()
                    cur.close()

                    cur = mysql.connection.cursor()
                    stype = source
                    status = "Deposit"
                    amount1 = int(amount)
                    accid1 = result2[0]['accid']
                    cid1 = cid
                    dtype = dest
                    cur.execute(
                        "INSERT INTO transactions(cid,accid,stype,dtype,status,amount) VALUES(%s,%s,%s,%s,%s,%s)",
                        [cid1, accid1 , stype, dtype, status, amount1])
                    mysql.connection.commit()
                    cur.close()

                    cur = mysql.connection.cursor()
                    stype = source
                    status = "Withdrawal"
                    amount2 = int(amount)
                    accid2 = result1[0]['accid']
                    cid2 = cid
                    dtype = dest
                    cur.execute(
                        "INSERT INTO transactions(cid,accid,stype,dtype,status,amount) VALUES(%s,%s,%s,%s,%s,%s)",
                        [cid2 , accid2 , stype, dtype, status, amount2])
                    mysql.connection.commit()
                    cur.close()

                    flash('Successfully Transferred','success')
                    return redirect('/cashier')
            else:
                flash("Either Any Type of Bank Account is not Available",'danger')
                return redirect('/cashier')
    elif request.method == 'GET':
        return 'get'
    return 'nothing'

#------------------------------------------------------------------------------------------------------------------
#Account View
@app.route('/account_view')
@is_logged_in
def account_view():
    return render_template('account_view.html')

@app.route('/account_view_status',methods=['POST','GET'])
@is_logged_in
def account_view_status():
    if request.method=='POST':
        accid = request.form['accid']
        cur = mysql.connection.cursor()
        data = cur.execute('select * from accounts where accid = %s',[accid])
        if data > 0:
            result = cur.fetchall()
            cur.close()
            return render_template('account_view_status.html', result=result)
        else :
            return render_template('account_view_status.html')

@app.route('/account_view_status_res/<string:cid>',methods=['GET','POST'])
@is_logged_in
def account_view_status_res(cid):
    if request.method == "POST":
        cur = mysql.connection.cursor()
        data = cur.execute('select * from accounts where accid = %s',[cid])
        if data > 0:
            result = cur.fetchall()
            return render_template('account_view_status_res.html',result=result)
#----------------------------------------------------------------------------------------------------------------------

@app.route('/account_statement',methods=['POST','GET'])
@is_logged_in
def account_statement():
    if request.method == 'POST':
        accid = request.form['accid']
        days = request.form['days']
        sod = request.form['sod']
        eod = request.form['eod']
        if(days and (sod or eod)):
            flash("Choose Either Number of days or Start/End Date",'danger')
            return render_template('account_statement.html')

        elif(days):
            cur = mysql.connection.cursor()
            # get the data from db
            data = cur.execute('select * from transactions where accid = %s order by time desc limit %s', [accid,int(days)])
            if(data > 0):
                result = cur.fetchall()
                mysql.connection.commit()
                cur.close()
                return render_template('account_statement_days.html', data=result, day=days)
            else :
                return render_template('account_statement.html',data=None)

        elif(sod):
            if(eod):
                cur = mysql.connection.cursor()
                # get the data from db
                data = cur.execute('select * from transactions where accid = %s and tdate between %s and %s order by time desc', [accid,sod,eod])
                if(data > 0):
                    result = cur.fetchall()
                    mysql.connection.commit()
                    cur.close()
                    return render_template('account_statement_date.html', data=result, sod=sod, eod=eod)
                else:
                    return render_template('account_statement.html', data=None)
            else:
                flash("Choose End Date",'danger')
                return render_template('account_statement.html')


        elif (eod):
            if (sod):
                cur = mysql.connection.cursor()
                # get the data from db
                data = cur.execute('select * from transactions where accid = %s and tdate between %s and %s',
                                   [accid, sod, eod])
                if (data > 0):
                    result = cur.fetchall()
                    mysql.connection.commit()
                    cur.close()
                    return render_template('account_statement_date.html', data=result, sod=sod, eod=eod)
                else:
                    return render_template('account_statement.html', data=None)
            else:
                flash("Choose Start Date",'danger')
                return render_template('account_statement.html')
        else:
            flash("Select Mandatory Fields",'danger')
            return render_template('account_statement.html')


    elif request.method == 'GET':
        return render_template('account_statement.html')

#----------------------------------------------------------------------------------------
@app.route('/downloadpdfday/<accid>/<limit>')
def downloadpdfday(accid,limit):
    # conn = None
    # cursor = None
    # conn = mysql.connect()
    # cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor = mysql.connection.cursor()
    cursor.execute('select * from transactions where accid = %s order by time desc limit %s',
                [accid, int(limit)])
    result = cursor.fetchall()
    #print(result)
    pdf = fpdf.FPDF()
    pdf.add_page()

    page_width = pdf.w - 2 * pdf.l_margin

    pdf.set_font('Times', 'B', 14.0)
    pdf.cell(page_width, 0.0, 'Account Statement', align='C')
    pdf.ln(10)
    pdf.cell(page_width, 0.0, 'Account ID', align='C')
    pdf.ln(10)
    pdf.cell(page_width, 0.0, str(result[0]['accid']) , align='C')
    pdf.ln(10)
    pdf.set_font('Courier', '', 12)

    col_width = page_width / 4

    pdf.ln(1)

    th = pdf.font_size

    for row in result:
        pdf.cell(col_width, th, str(row['tid']), border=1)
        pdf.cell(col_width, th, row['status'], border=1)
        pdf.cell(col_width, th, str(row['tdate']), border=1)
        pdf.cell(col_width, th, str(row['amount']), border=1)
        pdf.ln(th)

    pdf.ln(10)

    pdf.set_font('Times', '', 10.0)
    pdf.cell(page_width, 0.0, '- end of report -', align='C')

    return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment;filename=account_statement.pdf'})


#-------------------------------------------------------------------------------------

@app.route('/downloadexcelday/<accid>/<limit>')
def downloadexcelday(accid,limit):
    cursor = mysql.connection.cursor()
    cursor.execute('select tid,status,time,amount from transactions where accid = %s order by time desc limit %s', [accid,int(limit)])
    result = cursor.fetchall()
    book = xlwt.Workbook()
    sheet1 = book.add_sheet('Account-Statement')
    sheet1.write(0, 0, 'Transaction ID')
    sheet1.write(0, 1, 'Description')
    sheet1.write(0, 2, 'Time')
    sheet1.write(0, 3, 'Amount')

    days = len(result)
    col = 0
    for r in range(2, days + 2):
        dict = result[col]
        col = col + 1
        out = []
        for k in dict.keys():
            out.append(dict[k])
        for i, e in enumerate(out):
            sheet1.write(r, i, e)
        out = []

    name = "account_statement.xls"
    book.save(name)

    mysql.connection.commit()
    cursor.close()
    cwd = os.getcwd()
    cas = cwd + '\\account_statement.xls'
    return send_file(cas, as_attachment=True)


#----------------------------------------------------------------------------------------

@app.route('/downloadpdfdate/<accid>/<sod>/<eod>')
def downloadpdfdate(accid,sod,eod):
    # conn = None
    # cursor = None
    # conn = mysql.connect()
    # cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor = mysql.connection.cursor()
    cursor.execute('select * from transactions where accid = %s and tdate between %s and %s order by time desc',
                                   [accid, sod, eod])
    result = cursor.fetchall()
    #print(result)
    pdf = fpdf.FPDF()
    pdf.add_page()

    page_width = pdf.w - 2 * pdf.l_margin

    pdf.set_font('Times', 'B', 14.0)
    pdf.cell(page_width, 0.0, 'Account Statement', align='C')
    pdf.ln(10)
    pdf.cell(page_width, 0.0, 'Account ID', align='C')
    pdf.ln(10)
    pdf.cell(page_width, 0.0, str(result[0]['accid']) , align='C')
    pdf.ln(10)
    pdf.set_font('Courier', '', 12)

    col_width = page_width / 4

    pdf.ln(1)

    th = pdf.font_size

    for row in result:
        pdf.cell(col_width, th, str(row['tid']), border=1)
        pdf.cell(col_width, th, row['status'], border=1)
        pdf.cell(col_width, th, str(row['tdate']), border=1)
        pdf.cell(col_width, th, str(row['amount']), border=1)
        pdf.ln(th)

    pdf.ln(10)

    pdf.set_font('Times', '', 10.0)
    pdf.cell(page_width, 0.0, '- end of report -', align='C')

    return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment;filename=account_statement.pdf'})


#--------------------------------------------------------------------------------------------------------------------
@app.route('/downloadexceldate/<accid>/<sod>/<eod>')
def downloadexceldate(accid,sod,eod):
    # conn = None
    # cursor = None
    # conn = mysql.connect()
    # cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor = mysql.connection.cursor()
    cursor.execute('select tid,status,time,amount from transactions where accid = %s and tdate between %s and %s order by time desc',
                                   [accid, sod, eod])
    result = cursor.fetchall()
    book = xlwt.Workbook()
    sheet1 = book.add_sheet('Account-Statement')
    sheet1.write(0, 0, 'Transaction ID')
    sheet1.write(0, 1, 'Description')
    sheet1.write(0, 2, 'Time')
    sheet1.write(0, 3, 'Amount')

    days = len(result)
    col = 0
    for r in range(2, days + 2):
        dict = result[col]
        col = col + 1
        out = []
        for k in dict.keys():
            out.append(dict[k])
        for i, e in enumerate(out):
            sheet1.write(r, i, e)
        out = []

    name = "account_statement.xls"
    book.save(name)

    mysql.connection.commit()
    cursor.close()
    cwd = os.getcwd()
    cas = cwd+'\\account_statement.xls'
    return send_file(cas , as_attachment=True)


#--------------------------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True)
