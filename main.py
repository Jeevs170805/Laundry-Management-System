import tkinter as tk
import random
from tkinter import messagebox
from tkinter.ttk import Combobox ,Treeview
from datetime import datetime, date, timedelta
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

root = tk.Tk()
root.geometry('500x600')
root.title("LAUNDRY MANAGEMENT SYSTEM")

locked_icon = tk.PhotoImage(file='locked.png')
unlocked_icon = tk.PhotoImage(file='unlocked.png')

bg_colour = '#273b7a'

def save_data(Data,data):
    with open(Data,'w') as file:
        json.dump(data,file,indent=4)

def load_data(Data):
    if os.path.exists(Data):
        with open(Data,'r') as file:
            return json.load(file)
    return {}


class Nod:
    def __init__(self, data=None):
        self.data = data
        self.next = None

class LinkedList:
    def __init__(self):
        self.head = None

    def load(self):
        data = load_data('customers.json')
        if isinstance(data, dict):
            for customer_id, customer_data in data.items():
                self.append({customer_id: customer_data})
        elif isinstance(data, list):
            for customer_data in data:
                for customer_id, customer_info in customer_data.items():
                    self.append({customer_id: customer_info})

    def save(self):
        data={}
        current_node=self.head
        while current_node:
            for key,value in current_node.data.items():
                data[key]=value
            current_node=current_node.next
        save_data('customers.json',data)

    def append(self, data):
        new_node = Nod(data)
        if self.head is None:
            self.head = new_node
        else:
            last_node = self.head
            while last_node.next:
                last_node = last_node.next
            last_node.next = new_node

    def search(self, customer_id):
        current_node = self.head
        while current_node:
            if customer_id in current_node.data:
                return current_node.data[customer_id]
            current_node = current_node.next
        return None

    def update(self, customer_id, new_name, new_block_number, new_number):
        current_node = self.head
        while current_node:
            if customer_id in current_node.data:
                current_node.data[customer_id][0]=new_name
                current_node.data[customer_id][2] = new_block_number
                current_node.data[customer_id][3]=new_number
                break
            current_node = current_node.next
        self.save()

    def get_all_data(self):
        data_list = []
        current = self.head
        while current:
            data_list.append(current.data)
            current = current.next
        return data_list

    def print_list(self):
        current_node = self.head
        while current_node:
            print(current_node.data, end=" -> ")
            current_node = current_node.next
        print("None")

l1=LinkedList()
l1.load()


class Node:
    def __init__(self, item=None, priority=None, next=None):
        self.item = item
        self.priority = priority
        self.next = next


class PQ:
    def __init__(self):
        self.start = None
        self.item_count = 0
        self.details = []  # Current orders
        self.history = []  # All orders (for reports)
        self.pending_orders = [] #Orders waiting for admin approval
        self.decline_orders = [] #Orders declined by admin

    def load(self):
        print("Loading orders...")
        try:
            with open('orders.json', 'r') as file:
                data = json.load(file)
            self.details = data.get('details', [])
            for order in self.details:
                self._push_to_queue(order['data'], order['priority'])

            with open('report.json', 'r') as file:
                data = json.load(file)
            self.history = data.get('history', [])

            with open('declined_orders.json', 'r') as file:
                data = json.load(file)
            self.decline_orders = data.get('decline', [])

        except Exception as e:
            print(f"Error loading orders: {e}")

    def save(self):
        data = {
            'details': [
                {'data': order['data'], 'priority': order['priority']}
                for order in self.details
            ]
        }
        try:
            with open('orders.json', 'w') as file:
                json.dump(data, file, indent=4)

            data = {
                'history': [
                    {'data': order['data'], 'priority': order['priority']}
                    for order in self.history
                ]
            }
            with open('report.json', 'w') as file:
                json.dump(data, file, indent=4)

            data = {
                'decline': [
                    {'data': order['data'], 'priority': order['priority']}
                    for order in self.decline_orders
                ]
            }
            with open('declined_orders.json', 'w') as file:
                json.dump(data, file, indent=4)

        except Exception as e:
            print(f"Error saving orders: {e}")

    def push(self, data, priority, save=True):
        self.pending_orders.append({'data': data, 'priority': priority})

        # Push to the priority queue
        self._push_to_queue(data, priority)

        # Push to current orders
        #self.details.append({'data': data, 'priority': priority})
        # Push to history for reporting
        #self.history.append({'data': data, 'priority': priority})

        if save:
                self.save()

    def _push_to_queue(self, data, priority):
        n = Node(data, priority)
        if not self.start or priority < self.start.priority:
            n.next = self.start
            self.start = n
        else:
            temp = self.start
            while temp.next and temp.next.priority <= priority:
                temp = temp.next
            n.next = temp.next
            temp.next = n
        self.item_count += 1

    def is_empty(self):
        return self.start is None

    def pop(self):
        if self.is_empty():
            tk.messagebox.showinfo("Work","All work completed")
            return None
        data = self.start.item
        self.start = self.start.next
        self.item_count -= 1
        # Remove the order from current details
        self.details = [order for order in self.details if order['data'] != data]
        self.save()
        return data

    def size(self):
        return self.item_count

    '''def get_all_data(self):
        data_list = []
        temp = self.start
        while temp is not None:
            data_list.append(temp.item)
            temp = temp.next
        return data_list
    '''

    def approve(self):
            order = self.pending_orders.pop()
            formatted_order = {'data': order['data'], 'priority': order['priority']}
            self.details.append(formatted_order)
            self.history.append(formatted_order)
            self.send_accept_email(formatted_order)
            self.save()

    def send_accept_email(self, order):
        customer_id = order['data']['Customer_id']
        customer_info = l1.search(customer_id)
        if not customer_info:
            print(f"No email found for customer ID: {customer_id}")
            return
        to_email = customer_info[5] # Assuming the email is stored at index 5
        from_email = ""
        from_password = ""
        subject = "Your Order Has Been Accept"
        body = f"Dear {customer_info[0]},\n\nWe have accepted your order on  {order['priority']} .\n\nBest regards,\nML Service"

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(from_email, from_password)
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            server.quit()
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")


    def decline(self):
        if self.pending_orders:
            order = self.pending_orders.pop()
            formatted_order = {'data': order['data'], 'priority': order['priority']}
            self.decline_orders.append(formatted_order)
            self.save()
            self.send_decline_email(formatted_order)

    def send_decline_email(self, order):
        customer_id = order['data']['Customer_id']
        customer_info = l1.search(customer_id)
        if not customer_info:
            print(f"No email found for customer ID: {customer_id}")
            return
        to_email = customer_info[5] # Assuming the email is stored at index 5
        from_email = "kamalika2310617@ssn.edu.in"
        from_password = "sbvl ayqd xonl ndht"
        subject = "Your Order Has Been Declined"
        body = f"Dear {customer_info[0]},\n\nWe regret to inform you that your order in  {order['priority']} has been declined.\n\nBest regards,\nML Service"

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(from_email, from_password)
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            server.quit()
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")


    def get_pending_orders(self):
        return self.pending_orders

    def get_orders_data(self):
        return self.details

    def get_report_data(self):
        return self.history

    def __str__(self):
        items = []
        temp = self.start
        while temp is not None:
            items.append(f"({temp.item}, {temp.priority})")
            temp = temp.next
        return " -> ".join(items)

pq = PQ()


def welcome_page():
    def forward_to_customer_login_pg():
        welcome_pg.destroy()
        root.update()
        customer_login_page()

    def forward_to_admin_pg():
        welcome_pg.destroy()
        root.update()
        admin_login_page()

    def forward_to_new_customer_pg():
        welcome_pg.destroy()
        root.update()
        new_customer_page()

    welcome_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    welcome_pg.pack(pady=30)
    welcome_pg.pack_propagate(False)
    welcome_pg.configure(width=400, height=420)

    heading_lb = tk.Label(welcome_pg, text="WELCOME TO ML SERVICE", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=400)

    customer_login_bt = tk.Button(welcome_pg, text=" Customer Login", bg=bg_colour, fg='white', font=('Bold', 15), bd=0, command=forward_to_customer_login_pg)
    customer_login_bt.place(x=100, y=100, width=200)

    admin_login_bt = tk.Button(welcome_pg, text=" Admin Login", bg=bg_colour, fg='white', font=('Bold', 15), bd=0, command=forward_to_admin_pg)
    admin_login_bt.place(x=100, y=200, width=200)

    new_login_bt = tk.Button(welcome_pg, text="  New Customer", bg=bg_colour, fg='white', font=('Bold', 15), bd=0, command=forward_to_new_customer_pg)
    new_login_bt.place(x=100, y=300, width=200)


def customer_login_page():
    def forward_to_welcome_page():
        customer_login_pg.destroy()
        root.update()
        welcome_page()

    def show_hide_password():
        if password_input['show'] == '*':
            password_input.config(show='')
            show_hide_btn.config(image=unlocked_icon)
        else:
            password_input.config(show='*')
            show_hide_btn.config(image=locked_icon)

    def login_valid():
        customer_id=id_number_input.get()
        password=password_input.get()
        customer_data=l1.search(customer_id)
        if (customer_data!=None):
            password_data=customer_data[4]
            if (password_data == password):
                customer_login_pg.destroy()
                customer_page(customer_id)

            else:
                password_input.config(highlightcolor='red', highlightbackground='red')
                tk.messagebox.showerror("Error","Incorrect Password")
        else:
            id_number_input.config(highlightcolor='red', highlightbackground='red')
            tk.messagebox.showerror("Error","Incorrect User ID")


    customer_login_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    customer_login_pg.pack(pady=30)
    customer_login_pg.pack_propagate(False)
    customer_login_pg.configure(width=400, height=420)

    heading_lb = tk.Label(customer_login_pg, text="  CUSTOMER LOGIN", bg=bg_colour, fg='white', font=('Bold', 18))
    heading_lb.place(x=0, y=0, width=400)

    back_btn = tk.Button(customer_login_pg, text='<', font=('Bold', 20), fg=bg_colour, bd=0, command=forward_to_welcome_page)
    back_btn.place(x=5, y=40)

    id_number = tk.Label(customer_login_pg, text=" Enter Customer ID Number", fg=bg_colour, font=('Bold', 15))
    id_number.place(x=80, y=80)

    id_number_input = tk.Entry(customer_login_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2)
    id_number_input.place(x=90, y=130)

    password = tk.Label(customer_login_pg, text="Enter Customer Password", fg=bg_colour, font=('Bold', 15))
    password.place(x=90, y=200)

    password_input = tk.Entry(customer_login_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2, show='*')
    password_input.place(x=90, y=250)

    show_hide_btn = tk.Button(customer_login_pg, image=locked_icon, bd=0, command=show_hide_password)
    show_hide_btn.place(x=320, y=240)

    login_btn = tk.Button(customer_login_pg, text=" Login", bg=bg_colour, font=('Bold', 15), fg='white', command=login_valid)
    login_btn.place(x=100, y=340, width=200)


def admin_login_page():

    def forward_to_welcome_page():
        admin_login_pg.destroy()
        root.update()
        welcome_page()

    def show_hide_password():
        if password_input['show'] == '*':
            password_input.config(show='')
            show_hide_btn.config(image=unlocked_icon)
        else:
            password_input.config(show='*')
            show_hide_btn.config(image=locked_icon)

    def check_validity():
        admin_id=username_number_input.get()
        password=password_input.get()
        if(admin_id=="ML" and password=="1234"):
            admin_login_pg.destroy()
            admin_page()
        elif(admin_id!="ML"):
            username_number_input.config(highlightcolor='gray', highlightbackground='red')
            tk.messagebox.showerror("Error", "Incorrect Username")
        elif(password!="1234"):
            password_input.config(highlightcolor='gray', highlightbackground='red')
            tk.messagebox.showerror("Error", "Incorrect Password")


    admin_login_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    admin_login_pg.pack(pady=30)
    admin_login_pg.pack_propagate(False)
    admin_login_pg.configure(width=400, height=450)

    heading_lb = tk.Label(admin_login_pg, text=" ADMIN LOGIN", bg=bg_colour, fg='white', font=('Bold', 18))
    heading_lb.place(x=0, y=0, width=400)

    back_btn = tk.Button(admin_login_pg, text='<', font=('Bold', 20), fg=bg_colour, bd=0, command=forward_to_welcome_page)
    back_btn.place(x=5, y=40)

    username_number = tk.Label(admin_login_pg, text="         Enter Username", fg=bg_colour, font=('Bold', 15))
    username_number.place(x=80, y=80)

    username_number_input = tk.Entry(admin_login_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2)
    username_number_input.place(x=90, y=130)

    password = tk.Label(admin_login_pg, text="  Enter Admin Password", fg=bg_colour, font=('Bold', 15))
    password.place(x=90, y=200)

    password_input = tk.Entry(admin_login_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2, show='*')
    password_input.place(x=90, y=250)

    show_hide_btn = tk.Button(admin_login_pg, image=locked_icon, bd=0, command=show_hide_password)
    show_hide_btn.place(x=320, y=240)

    login_btn = tk.Button(admin_login_pg, text=" Login", bg=bg_colour, font=('Bold', 15), fg='white', command=check_validity)
    login_btn.place(x=100, y=340, width=200)


def new_customer_page():
    def forward_to_welcome_page():
        add_account_pg.destroy()
        root.update()
        welcome_page()

    def generate_id():
        id = ''.join(str(random.randint(0, 9)) for _ in range(6))
        customer_id_input.config(state=tk.NORMAL)
        customer_id_input.delete(0, tk.END)
        customer_id_input.insert(tk.END, id)
        customer_id_input.config(state='readonly')

    def get_data():
        data = []
        customer_id_data = customer_id_input.get()
        name_data = customer_name_input.get()
        gender_data = customer_gender.get()
        block_number_data = block_number_input.get()
        number = number_input.get()
        mail=email_input.get()
        password = create_password_input.get()
        data.append(customer_id_data)
        data.append(name_data)
        data.append(gender_data)
        data.append(block_number_data)
        data.append(number)
        data.append(password)
        data.append(mail)
        return data

    def add_data():
        data = {}
        values = get_data()
        data[values[0]] = values[1:7]
        l1.append(data)
        l1.save()
        tk.messagebox.showinfo("Success","Customer Added Successfully")

    def check_validity():
        password = create_password_input.get()
        name = customer_name_input.get()
        block = block_number_input.get()
        number =number_input.get()
        mail = email_input.get()
        if (name == ""):
            customer_name_input.config(highlightcolor='gray', highlightbackground='red')
            tk.messagebox.showerror("Name","Enter Name")
        elif (block == "" or block.isdigit()!=True):
            block_number_input.config(highlightcolor='gray', highlightbackground='red')
            tk.messagebox.showerror("Block Number","Enter Valid Block Number")
        elif (number == "" or block.isdigit()!=True):
            number_input.config(highlightcolor='gray', highlightbackground='red')
            tk.messagebox.showerror("Mobile Number","Enter Valid Mobile Number")
        elif (mail== ""):
            email_input.config(highlightcolor='gray', highlightbackground='red')
            tk.messagebox.showerror("Email","Enter Valid email")
        elif (password == ""):
            create_password_input.config(highlightcolor='gray', highlightbackground='red')
            tk.messagebox.showerror("Password","Enter Password")
        else:
            return "Correct"

    def combined_command():
        if check_validity()=="Correct":
            add_data()
            forward_to_welcome_page()


    add_account_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    add_account_pg.pack(pady=5)
    add_account_pg.pack_propagate(False)
    add_account_pg.configure(width=480, height=580)

    heading_lb = tk.Label(add_account_pg, text="NEW CUSTOMER SIGNUP", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=480)

    customer_name = tk.Label(add_account_pg, text="Enter Full Name Of the Customer", font=('Bold', 12))
    customer_name.place(x=5, y=60)

    customer_name_input = tk.Entry(add_account_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2)
    customer_name_input.place(x=5, y=95)

    customer_gender = tk.Label(add_account_pg, text="Select Customer Gender", font=('Bold', 12))
    customer_gender.place(x=5, y=140)

    customer_gender = tk.StringVar()
    customer_gender.set('Male')

    male_gender_btn = tk.Radiobutton(add_account_pg, text="Male", font=('Bold', 12), variable=customer_gender, value='Male')
    male_gender_btn.place(x=5, y=175)

    female_gender_btn = tk.Radiobutton(add_account_pg, text="Female", font=('Bold', 12), variable=customer_gender, value='Female')
    female_gender_btn.place(x=75, y=175)

    block_number = tk.Label(add_account_pg, text="Enter The Block Number", font=('Bold', 12))
    block_number.place(x=5, y=225)

    block_number_input = tk.Entry(add_account_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2)
    block_number_input.place(x=5, y=265)

    number = tk.Label(add_account_pg, text="Enter Mobile Number", font=('Bold', 12))
    number.place(x=5, y=300)

    number_input = tk.Entry(add_account_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2)
    number_input.place(x=5, y=335)

    customer_id = tk.Label(add_account_pg, text="CUSTOMER ID", font=('Bold', 12))
    customer_id.place(x=250, y=95)

    customer_id_input = tk.Entry(add_account_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2)
    customer_id_input.place(x=370, y=95, width=90)
    customer_id_input.config(state='readonly')
    generate_id()

    email = tk.Label(add_account_pg, text="Enter Email Address", font=('Bold', 12))
    email.place(x=5, y=370)

    email_input = tk.Entry(add_account_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2)
    email_input.place(x=5, y=405)

    create_password = tk.Label(add_account_pg, text="Create A New Password", font=('Bold', 12))
    create_password.place(x=250, y=150)

    create_password_input = tk.Entry(add_account_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour, highlightbackground='gray', highlightthickness=2)
    create_password_input.place(x=250, y=185, width=200)

    home_btn = tk.Button(add_account_pg, text="HOME", font=('Bold', 15), bg='red', fg='white', bd=0, command=forward_to_welcome_page)
    home_btn.place(x=250, y=250)

    submit_btn = tk.Button(add_account_pg, text="SUBMIT", font=('Bold', 15), bg=bg_colour, fg='white', bd=0, command=combined_command)
    submit_btn.place(x=360, y=250)


def customer_page(customer_id):

    def forward_to_welcome_page():
        customer_pg.destroy()
        root.update()
        welcome_page()

    def combined():
        clothes_number=clothes_input.get()
        type_data=type_input.get()
        priority=urg_input.get()
        sum=0
        if(type_data=="Wash and Dry"):
            sum=int(clothes_number)*7
        elif(type_data=="Wash and Press"):
            sum=int(clothes_number)*10
        elif(type_data=="Steam Press"):
            sum=int(clothes_number)*15
        elif(type_data=="Heavy duty"):
            sum=int(clothes_number)*20

        today=date.today()
        if priority=="yes":
            delivery=today+ timedelta(days=1)
        else:
            delivery=today+ timedelta(days=4)

        tk.messagebox.showinfo("Transaction Slip", f"Deposit date:{today}\nNumber Of clothes:{clothes_number}\nType Of Wash:{type_data}\nTotal Price:{sum}\nDelivery Date:{str(delivery)}")
        data={"Customer_id":customer_id,"Delivery date":str(delivery),"Number of clothes":clothes_number,"Type of wash":type_data,"Price":sum}
        pq.push(data,str(delivery))
        customer_pg.destroy()
        welcome_page()

    type_list=["Wash and Dry","Wash and Press","Steam Press","Heavy duty"]
    customer_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    customer_pg.pack(pady=30)
    customer_pg.pack_propagate(False)
    customer_pg.configure(width=400, height=600)

    heading_lb = tk.Label(customer_pg, text="LAUNDRY DETAILS", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=400)

    price = tk.Label(customer_pg, text="        PRICE\n\n     Wash and dry: Rs 7\n    Heavy Duty: Rs 20\n      Steam Press: Rs 15\n        Wash and Press: Rs 10", fg=bg_colour, font=('Bold', 15))
    price.place(x=50, y=80)

    clothes = tk.Label(customer_pg, text=" Enter The Number Of the Clothes", fg=bg_colour, font=('Bold', 15))
    clothes.place(x=50, y=250)

    clothes_input = tk.Entry(customer_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour,
                               highlightbackground='gray', highlightthickness=2)
    clothes_input.place(x=85, y=290)

    type = tk.Label(customer_pg, text="  Enter The Type Of Laundry", fg=bg_colour, font=('Bold', 15))
    type.place(x=70, y=340)

    type_input = Combobox(customer_pg,font=('Bold',15),
                          state='readonly', values=type_list)
    type_input.place(x=95, y=380, width=200, height=30)

    urg = tk.Label(customer_pg,text=" Is your delivery urgent?(yes/no)",fg=bg_colour, font=('Bold', 15))
    urg.place(x=50,y=430)

    urg_input = tk.Entry(customer_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour,
                   highlightbackground='gray',highlightthickness=2)
    urg_input.place(x=85,y=470)

    order_btn = tk.Button(customer_pg, text="Order", bg=bg_colour, font=('Bold', 15), fg='white',command=combined)
    order_btn.place(x=45, y=530, width=300)

    back_btn = tk.Button(customer_pg, text='<', font=('Bold', 20), fg=bg_colour, bd=0,
                         command=forward_to_welcome_page)
    back_btn.place(x=5, y=40)


def admin_page():

    def forward_to_welcome_page():
        admin_pg.destroy()
        welcome_page()

    def forward_to_details():
        admin_pg.destroy()
        customer_details_page()

    def forward_to_view():
        admin_pg.destroy()
        view_page()

    def forward_to_report():
        admin_pg.destroy()
        report_page()

    def forward_to_approve_orders():
        admin_pg.destroy()
        approve_orders_page()

    admin_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    admin_pg.pack(pady=30)
    admin_pg.pack_propagate(False)
    admin_pg.configure(width=400, height=510)

    heading_lb = tk.Label(admin_pg, text="ADMIN PAGE", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=400)

    view_customer_bt = tk.Button(admin_pg, text="Customer Details", bg=bg_colour, fg='white', font=('Bold', 15), bd=0,
                        command=forward_to_details)
    view_customer_bt.place(x=100, y=110, width=200)

    work_bt = tk.Button(admin_pg, text=" Work", bg=bg_colour, fg='white', font=('Bold', 15), bd=0,command=forward_to_view)
    work_bt.place(x=100, y=210, width=200)

    report_bt = tk.Button(admin_pg, text=" Report", bg=bg_colour, fg='white', font=('Bold', 15), bd=0,command=forward_to_report)
    report_bt.place(x=100, y=310, width=200)

    approve_orders_bt = tk.Button(admin_pg, text="Approve Orders", bg=bg_colour, fg='white', font=('Bold', 15), bd=0, command=forward_to_approve_orders)
    approve_orders_bt.place(x=100, y=410, width=200)


    back_btn = tk.Button(admin_pg, text='<', font=('Bold', 20), fg=bg_colour, bd=0,
                         command=forward_to_welcome_page)
    back_btn.place(x=5, y=40)


def customer_details_page():
    def forward_to_update():
        customer_details_pg.destroy()
        root.update()
        update_page()

    def forward_to_admin_page():
        customer_details_pg.destroy()
        root.update()
        admin_page()

    customer_details_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    customer_details_pg.pack(pady=30)
    customer_details_pg.pack_propagate(False)
    customer_details_pg.configure(width=1050, height=850)

    heading_lb = tk.Label(customer_details_pg, text="CUSTOMER DETAILS", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=1050)

    tree = Treeview(customer_details_pg, columns=('Customer ID', 'Name', 'Gender', 'Block Number', 'Mobile Number'),
                    show='headings')
    tree.heading('Customer ID', text='Customer ID')
    tree.heading('Name', text='Name')
    tree.heading('Gender', text='Gender')
    tree.heading('Block Number', text='Block Number')
    tree.heading('Mobile Number', text='Mobile Number')
    tree.column('Customer ID', anchor=tk.CENTER)
    tree.column('Name', anchor=tk.CENTER)
    tree.column('Gender', anchor=tk.CENTER)
    tree.column('Block Number', anchor=tk.CENTER)
    tree.column('Mobile Number', anchor=tk.CENTER)
    tree.place(x=20, y=100, width=970, height=300)

    all_customer_data = l1.get_all_data()
    for customer_data in all_customer_data:
        customer_id = list(customer_data.keys())[0]
        data = customer_data[customer_id]
        tree.insert('', tk.END, values=(customer_id, data[0], data[1], data[2], data[3]))

    back_btn = tk.Button(customer_details_pg, text='<', font=('Bold', 20), fg=bg_colour, bd=0,
                         command=forward_to_admin_page)
    back_btn.place(x=5, y=40)

    update_btn = tk.Button(customer_details_pg, text="Update Customer Details ", bg=bg_colour, font=('Bold', 15), fg='white', command=forward_to_update)
    update_btn.place(x=620, y=500, width=300)


def update_page():
    def combined():
        customer_id_data = customer_id_input.get()
        new_name = customer_name_input.get()
        new_block_number = block_number_input.get()
        new_number = number_input.get()
        l1.update(customer_id_data, new_name, new_block_number, new_number)
        tk.messagebox.showinfo("Success", "Customer details updated successfully.")
        update_pg.destroy()
        admin_page()

    update_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    update_pg.pack(pady=5)
    update_pg.pack_propagate(False)
    update_pg.configure(width=480, height=580)

    heading_lb = tk.Label(update_pg, text="UPDATE DETAILS", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=480)

    customer_id = tk.Label(update_pg, text="Customer ID", font=('Bold', 12))
    customer_id.place(x=5, y=60)

    customer_id_input = tk.Entry(update_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour,
                                   highlightbackground='gray', highlightthickness=2)
    customer_id_input.place(x=5, y=95)

    customer_name = tk.Label(update_pg, text="Change Name", font=('Bold', 12))
    customer_name.place(x=5, y=140)

    customer_name_input = tk.Entry(update_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour,
                                 highlightbackground='gray', highlightthickness=2)
    customer_name_input.place(x=5, y=175)

    block_number = tk.Label(update_pg, text="Change Block Number", font=('Bold', 12))
    block_number.place(x=5, y=225)

    block_number_input = tk.Entry(update_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour,
                                  highlightbackground='gray', highlightthickness=2)
    block_number_input.place(x=5, y=265)

    number = tk.Label(update_pg, text="Change Mobile Number", font=('Bold', 12))
    number.place(x=5, y=300)

    number_input = tk.Entry(update_pg, font=('Bold', 15), justify=tk.CENTER, highlightcolor=bg_colour,
                            highlightbackground='gray', highlightthickness=2)
    number_input.place(x=5, y=335)

    submit_btn = tk.Button(update_pg, text="SUBMIT", font=('Bold', 15), bg=bg_colour, fg='white', bd=0,
                           command=combined)
    submit_btn.place(x=5, y=450)


def view_page():

    def completed():
        pq.pop()
        display()

    def view():
        display()

    def forward_to_welcome_page():
        view_pg.destroy()
        admin_page()

    view_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    view_pg.pack(pady=30)
    view_pg.pack_propagate(False)
    view_pg.configure(width=800, height=850)

    heading_lb = tk.Label(view_pg, text="WORK PAGE", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=800)

    def display():
        tree=Treeview(view_pg,columns=('Customer_id','Delivery date','Number of clothes','Price'),show='headings')
        tree.heading('Customer_id',text='Customer_ID')
        tree.heading('Delivery date',text='Delivery date')
        tree.heading('Number of clothes',text='Number of Clothes')
        tree.heading('Price',text='Price')
        tree.column('Customer_id',anchor=tk.CENTER)
        tree.column('Delivery date', anchor=tk.CENTER)
        tree.column('Number of clothes', anchor=tk.CENTER)
        tree.column('Price', anchor=tk.CENTER)
        tree.place(x=20,y=100,width=750,height=300)

        all_data=pq.get_orders_data()
        for i in all_data:
            data = i['data']
            tree.insert('',tk.END,values=(data["Customer_id"],data["Delivery date"],data["Number of clothes"], data["Price"]))

    back_btn = tk.Button(view_pg, text='<', font=('Bold', 20), fg=bg_colour, bd=0,command=forward_to_welcome_page)
    back_btn.place(x=5, y=40)

    completed_btn = tk.Button(view_pg, text="Completed ", bg=bg_colour, font=('Bold', 15), fg='white',command=completed)
    completed_btn.place(x=600, y=500, width=180)

    show_btn = tk.Button(view_pg, text="Show ", bg=bg_colour, font=('Bold', 15), fg='white',command=view)
    show_btn.place(x=600, y=600, width=180)


def report_page():

    def forward_to_welcome_page():
        report_pg.destroy()
        admin_page()

    report_pg = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    report_pg.pack(pady=30)
    report_pg.pack_propagate(False)
    report_pg.configure(width=800, height=850)

    heading_lb = tk.Label(report_pg, text="REPORT PAGE", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=800)

    tree = Treeview(report_pg, columns=('Customer_id','Date','Price'), show='headings')
    tree.heading('Customer_id', text='Customer_ID')
    tree.heading('Date',text='Deposit Date')
    tree.heading('Price', text='Price')
    tree.column('Customer_id', anchor=tk.CENTER)
    tree.column('Date',anchor=tk.CENTER)
    tree.column('Price', anchor=tk.CENTER)
    tree.place(x=20, y=100, width=750, height=300)

    today=date.today()
    all_data=pq.get_report_data()
    for i in all_data:
        data = i['data']
        tree.insert('', tk.END,values=(data["Customer_id"],today,data["Price"]))

    back_btn = tk.Button(report_pg, text='<', font=('Bold', 20), fg=bg_colour, bd=0,
                         command=forward_to_welcome_page)
    back_btn.place(x=5, y=40)


def approve_orders_page():
    def forward_to_admin_page():
        approve_orders_page.destroy()
        admin_page()

    def approve_order():
        """selected_item = tree.selection()
        if selected_item:
            index = int(tree.item(selected_item[0], "text"))"""
        pq.approve()
        display_pending_orders()

    def decline_order():
        """selected_item = tree.selection()
        if selected_item:
            index = int(tree.item(selected_item[0], "text"))"""
        pq.decline()
        display_pending_orders()

    def display_pending_orders():
        tree.delete(*tree.get_children())
        pending_orders = pq.get_pending_orders()
        for index, order in enumerate(pending_orders):
            data = order['data']
            tree.insert('', tk.END, text=index, values=(data['Customer_id'], data['Delivery date'], data['Price']))

    approve_orders_page = tk.Frame(root, highlightbackground=bg_colour, highlightthickness=3)
    approve_orders_page.pack(pady=30)
    approve_orders_page.pack_propagate(False)
    approve_orders_page.configure(width=800, height=850)

    heading_lb = tk.Label(approve_orders_page, text="APPROVE ORDERS", bg=bg_colour, fg="white", font=("Bold", 15))
    heading_lb.place(x=0, y=0, width=800)

    tree = Treeview(approve_orders_page, columns=('Customer_id', 'Delivery date', 'Price'), show='headings')
    tree.heading('Customer_id', text='Customer_ID')
    tree.heading('Delivery date', text='Delivery Date')
    tree.heading('Price', text='Price')
    tree.column('Customer_id', anchor=tk.CENTER)
    tree.column('Delivery date', anchor=tk.CENTER)
    tree.column('Price', anchor=tk.CENTER)
    tree.place(x=20, y=100, width=750, height=300)

    # Initially display pending orders
    display_pending_orders()

    # Button to approve selected order
    approve_btn = tk.Button(approve_orders_page, text="Approve Order", bg=bg_colour, font=('Bold', 15), fg='white', command=approve_order)
    approve_btn.place(x=530, y=500, width=180)

    decline_btn = tk.Button(approve_orders_page, text="Decline Order", bg=bg_colour, font=('Bold', 15), fg='white', command=decline_order)
    decline_btn.place(x=70, y=500, width=180)

    # Back button to return to the admin page
    back_btn = tk.Button(approve_orders_page, text='<', font=('Bold', 20), fg=bg_colour, bd=0, command=forward_to_admin_page)
    back_btn.place(x=5, y=40)



welcome_page()
root.mainloop()



