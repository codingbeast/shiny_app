Certainly, my lord. Below are the detailed instructions to **deploy a Flask app (`app.py`) on Amazon Linux using Nginx and Gunicorn**. This guide assumes you're deploying on an EC2 instance running Amazon Linux 2.

---

## 🛠️ Step-by-Step Deployment Guide for Flask App (`app.py`) on Amazon Linux using Nginx

### ✅ 1. **Update the System**

```bash
sudo yum update -y
```

---

### ✅ 2. **Install Python3, pip, and venv**

Amazon Linux 2 comes with Python 3.7+, but install it just in case:

```bash
sudo yum install python3 -y
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### ✅ 3. **Install Flask and Gunicorn**

```bash
pip install flask gunicorn
```

Your directory structure should look like:

```
/home/ec2-user/myflaskapp/
│
├── app.py
├── venv/
```

---

### ✅ 4. **Create a Flask App**

If not already done, here is an example `app.py`:

```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, my lord. Flask is running!"
```

---

### ✅ 5. **Run Gunicorn**

Test it with:

```bash
gunicorn --bind 0.0.0.0:8000 app:app
```

* `app:app` means: `app.py` file and `app` is the Flask app instance.

---

### ✅ 6. **Install and Configure Nginx**

```bash
sudo amazon-linux-extras install nginx1 -y
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

### ✅ 7. **Configure Nginx as a Reverse Proxy**

Edit the default Nginx configuration:

```bash
sudo nano /etc/nginx/nginx.conf
```

Add this inside the `http {}` block, or better, create a new file under `/etc/nginx/conf.d/flaskapp.conf`.

Example `/etc/nginx/conf.d/flaskapp.conf`:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Restart Nginx:

```bash
sudo systemctl restart nginx
```

---

### ✅ 8. **Set Up a Gunicorn Systemd Service**

Create a service file for Gunicorn:

```bash
sudo nano /etc/systemd/system/myflaskapp.service
```

Paste:

```ini
[Unit]
Description=Gunicorn instance to serve myflaskapp
After=network.target

[Service]
User=ec2-user
Group=nginx
WorkingDirectory=/home/ec2-user/myflaskapp
Environment="PATH=/home/ec2-user/myflaskapp/venv/bin"
ExecStart=/home/ec2-user/myflaskapp/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl start myflaskapp
sudo systemctl enable myflaskapp
```

---

### ✅ 9. **Adjust Firewall (if needed)**

If using EC2, ensure your **Security Group** allows **port 80 (HTTP)** from anywhere (0.0.0.0/0).

---

### ✅ 10. **Test Your Application**

Open your EC2 public IP or domain name in a browser:

```
http://<your-ec2-public-ip>/
```

You should see:

> Hello, my lord. Flask is running!

---

## 🔁 Optional: Setup Domain and SSL with Certbot (Bonus)

If you’re using a domain name:

```bash
sudo yum install -y certbot python3-certbot-nginx
sudo certbot --nginx
```

This will auto-configure HTTPS using Let’s Encrypt.

---