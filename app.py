import bcrypt
import time
from flask import Flask, request,url_for, redirect,session
from flask.helpers import flash
from flask.json import jsonify
from flask.templating import render_template, render_template_string
import database
import uuid

app = Flask(__name__)  # referencing this file
app.secret_key = "testing"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register',methods=['POST','GET'])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    msg =''
    
    if request.method == 'POST':

        register = request.form.to_dict()
        user_id = str(uuid.uuid4())
        register['user_id'] = user_id
        email_found = database.db['users'].find_one({'email': register['email']})
        
        if email_found : 
            msg = 'e-mail deja utilisé'
        elif register['password'] != register['password_repeat'] :
            msg = 'Le mot de passe n est pas compatible'
        else : 
            hashed = bcrypt.hashpw(register['password'].encode('utf-8'),bcrypt.gensalt())
            register['password'] = hashed
            register['subscription_date'] = time.strftime('%Y-%m-%d')
            del register['password_repeat']
            database.db['users'].insert_one(register)

            data = {'user_id':user_id,'p_id':"0",'o_id':"0",'suppliersandcustomers_id':"0",'valueInventory':0,'Income':0}
            database.db['data'].insert_one(data)

            session['user_id']= register['user_id']
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login',methods=['POST','GET'])
def login():
    if "user_id" in session : 
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        found = database.db['users'].find_one({'email':email})
        if found :
            print(found)
            passwordcheck = found['password']
            if bcrypt.checkpw(password.encode('utf-8'), passwordcheck):
                session["user_id"] = found['user_id']
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html',msg='ghalat fl pswrd')

        return render_template('login.html',msg='ghalat fl email')
               
    return render_template('login.html')

@app.route('/dashboard',methods=['POST','GET'])
def dashboard():
    if "user_id" in session:
        user_id = session['user_id']
        
        stockvalue = list(database.db['products'].find({'user_id':user_id},{'stock':1,'valeur':1}))
        newvalue = 0
        for value in stockvalue :
            newvalue += int(value['stock'])*int(value['valeur'])
        database.db['data'].update_one({'user_id':user_id},{"$set":{'valueInventory':newvalue}}) 
        
        userdata =list(database.db['data'].find({'user_id':user_id}))[0]
        userprofile = list(database.db['users'].find({'user_id':user_id}))[0]
        user = userdata | userprofile

        return render_template('dashboard.html',user = user)
    else:
        return redirect(url_for('login'))

# Products Route
@app.route('/products', methods=['POST', 'GET'])
def products():
    
    if "user_id" in session:
        #user data
        user_id = session["user_id"]
        userdata =list(database.db['data'].find({'user_id':user_id}))[0]
        userprofile = list(database.db['users'].find({'user_id':user_id}))[0]
        user = userdata | userprofile


        products = list(database.db["products"].find({'user_id':user_id}, {'_id': 0}))
        categories = list(database.db["Categories"].find())[0]

        for product in products:
            product["categorie"] = categories[product["categorie"]]
            if int(product["stock"]) > int(product["stockMinimal"]):
                product['state'] = "Disponible"

            if int(product['stock']) <= int(product['stockMinimal']) and int(product['stock']) != 0:
                product['state'] = "Bientôt épuisé"

            if int(product['stock']) == 0:
                product['state'] = "Épuisé"

        p_id = list(database.db["data"].find({'user_id':user_id}))[0]['p_id']
        old_pid = p_id
        if request.method == 'POST':

            product_id = "PR"

            if len(p_id) == 5:
                p_id = str(int(p_id) + 1)
                database.db['data'].update(
                    {'p_id': old_pid,'user_id':user_id}, {"$set": {'p_id': p_id}})
                product_id = product_id+p_id

            else:
                p_id = str(int(p_id) + 1)
                database.db['data'].update(
                    {'p_id': old_pid,'user_id':user_id}, {"$set": {'p_id': p_id}})
                while len(p_id) < 5:
                    p_id = "0"+p_id
                product_id = product_id+p_id

            product = request.form.to_dict()
            product['p_reference'] = product_id
            product['user_id'] = user_id

            value = int(product['valeur'])*int(product['stock'])
            old_value = database.db['data'].find_one({'user_id':user_id})['valueInventory']
            
            database.db['data'].update({'user_id':user_id},{"$set":{'valueInventory':old_value + value}})
            database.db["products"].insert_one(product)
            return redirect('/products')

        else:
            return render_template('products.html', products=products,user=user)
    else:
        return redirect(url_for('login'))

@app.route('/products/delete/<user_id>/<p_id>')
def productdelete(user_id,p_id):
    try:
        database.db["products"].delete_one({"p_reference": p_id,'user_id':user_id})

        return redirect('/products')
    except:
        return jsonify("Erreur : Produit selectionné ne peut pas être supprimer")

# Operations route
@app.route('/operations', methods=['POST', 'GET'])
def operation():
    
    if "user_id" in session:
        #user data
        user_id = session['user_id']
        userdata =list(database.db['data'].find({'user_id':user_id}))[0]
        userprofile = list(database.db['users'].find({'user_id':user_id}))[0]
        user = userdata | userprofile


        operations = list(database.db["operations"].find({'user_id':user_id}, {'_id': 0}))
        
        for op in operations:
            op['type'] = op['type'].capitalize()


        autocomplete = list(database.db['suppliersandcustomers'].find({'user_id':user_id},{'_id':0,'nomsociete':1}))
        companies =[]
        
        for ac in autocomplete:
            companies.append(ac['nomsociete'])    
        if request.method == "GET":
            return render_template('operation.html',operations= operations, companies=companies,user=user)
        

        o_id = list(database.db["data"].find({'user_id':user_id}))[0]['o_id']
        old_oid = o_id

        if request.method == 'POST':
            o_reference = "OP"
            operation = request.form.to_dict()

            if operation['type'] == 'entry':
                o_reference += "N"
            else:
                o_reference += "X"

            if len(o_id) == 4:
                o_id = str(int(o_id) + 1)
                database.db['data'].update(
                    {'o_id': old_oid,'user_id':user_id}, {"$set": {'o_id': o_id}})
                o_reference = o_reference+o_id
            else:
                o_id = str(int(o_id) + 1)
                database.db['data'].update_one(
                    {'o_id': old_oid,'user_id':user_id}, {"$set": {'o_id': o_id}})
                while len(o_id) < 4:
                    o_id = "0"+o_id
                o_reference = o_reference+o_id

            operation['o_reference'] = o_reference
            operation['user_id'] = user_id
            # Add change in products database 
            quantity = list(database.db['products'].find({'p_reference': operation['p_reference'],'user_id':user_id},{"_id": 0, "stock": 1}))[0]['stock']
            newvalue = quantity

            income = user['Income']
            if operation['type'] == 'entry': 
                newvalue = str(int(quantity)+int(operation['quantity']))
                income -= int(operation['quantity'])*int(operation['price'])

            else :
                newvalue = str(int(quantity)-int(operation['quantity']))
                income += int(operation['quantity'])*int(operation['price'])

            database.db['data'].update_one({'user_id':user_id}, {"$set": {'Income':income}})
            database.db['products'].update_one({'p_reference': operation['p_reference'],'user_id':user_id}, {"$set": {'stock':newvalue }})
            ########
        
            database.db["operations"].insert_one(operation)
            return redirect('/operations')
        else:
            return render_template('operation.html', operations=operations,user=user)
    else:
        return redirect(url_for('login'))

@app.route('/suppliersandcustomers', methods=['POST','GET'])
def suppliersandcustomers():
    if "user_id" in session:
        #user data
        user_id = session["user_id"]
        userdata =list(database.db['data'].find({'user_id':user_id}))[0]
        userprofile = list(database.db['users'].find({'user_id':user_id}))[0]
        user = userdata | userprofile


        suppliersandcustomers = list(database.db["suppliersandcustomers"].find({'user_id':user_id}, {'_id': 0}))

        for profile in suppliersandcustomers:
            profile['type'] = profile['type'].capitalize()

        suppliersandcustomers_id = list(database.db["data"].find({'user_id':user_id}))[0]['suppliersandcustomers_id']
        old_profileid = suppliersandcustomers_id


        if request.method == 'POST':

            profile_id = "U"

            type = request.form['type']
            if type == 'fournisseur' : 
                profile_id = profile_id +"F"
            else : 
                profile_id += "C"

            if len(suppliersandcustomers_id) == 5:
                suppliersandcustomers_id = str(int(suppliersandcustomers_id) + 1)
                database.db['data'].update_one(
                    {'suppliersandcustomers_id': old_profileid,'user_id':user_id}, {"$set": {'suppliersandcustomers_id': suppliersandcustomers_id}})
                profile_id = profile_id+suppliersandcustomers_id

            else:
                suppliersandcustomers_id = str(int(suppliersandcustomers_id) + 1)
                database.db['data'].update_one(
                    {'suppliersandcustomers_id': old_profileid,'user_id':user_id}, {"$set": {'suppliersandcustomers_id': suppliersandcustomers_id}})
                while len(suppliersandcustomers_id) < 5:
                    suppliersandcustomers_id = "0"+suppliersandcustomers_id
                profile_id = profile_id+suppliersandcustomers_id

            profile = request.form.to_dict()
            profile['profile_id'] = profile_id
            profile['user_id'] = user_id
            profile['n_op'] = 0

            database.db["suppliersandcustomers"].insert_one(profile)
            return redirect('/suppliersandcustomers')
        else:

            return render_template('suppliersandcustomers.html', profiles = suppliersandcustomers,user=user)
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    try:    
        del session['user_id']
        return redirect('/')
    except:
        return jsonify('already logged out')

if __name__ == "__main__":
    app.run(debug=True)

