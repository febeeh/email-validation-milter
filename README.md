# Email Validation Milter For Postfix
Python-based email validation milter using PyMilter that helps enforce sending limits per sender. It utilizes Redis for real-time tracking and throttling, ensuring compliance with predefined email policies.

## 🚀 Features
- Limits emails per sender over different time intervals:
  - `MAX_EMAILS_PER_5_MINUTES`
  - `MAX_EMAILS_PER_HR`
- Restricts the number of CC recipients (`MAX_CC_RECIPIENTS`)
- Controls the number of recipient addresses per email (`MAX_MAIL_ADDRESS_SINGLE_EMAIL`)
- Uses Redis for efficient tracking and validation
- Lightweight and fast integration with mail servers

## 🛠️ Installation

### Prerequisites
Ensure you have the following installed:

- Python 3.x
- Redis
- Postfix/Sendmail (or any mail server that supports milters)

### Steps
#### 1: Clone the repository
#### 2: Install dependencies:
```sh
pip install pymilter redis python-dotenv
```
#### 3: Set up your .env file
```sh
# Mail Milter Configuration
MAX_EMAILS_PER_5_MINUTES = 50 # Maximum emails allowed in 5 minutes
MAX_EMAILS_PER_HR = 100 # Maximum emails allowed in 1 hour
MAX_CC_RECIPIENTS = 15 # Maximum CC recipients allowed
MAX_EMAIL_SINGLE = 3 # Maximum emails allowed in a single request

# Redis
REDIS_HOST ="localhost" # Redis host
REDIS_PORT =6379 # Redis port
REDIS_PASSWORD ="password_here" # Redis password

# Socket Configuration
SOCKET_HOST = "localhost" # Socket host
SOCKET_PORT = 10032 # Socket port
```
#### 4: Start the milter:
```sh
python mail_throttle.py
```

### Integration with Postfix

#### 1: Add the milter in main.cf:
```sh
smtpd_milters = inet:localhost:10032
milter_default_action = accept
```
#### 2: Restart Postfix:
```sh
systemctl restart postfix
```
---

## Environment Variables

To configure the milter, set up the following environment variables:

### **Mail Milter Configuration**
| Variable                 | Description                              | Default Value |
|--------------------------|------------------------------------------|--------------|
| `MAX_EMAILS_PER_5_MINUTES` | Maximum emails allowed per 5 minutes    | `50`         |
| `MAX_EMAILS_PER_HR`       | Maximum emails allowed per hour         | `100`        |
| `MAX_CC_RECIPIENTS`       | Maximum CC recipients per email         | `15`         |
| `MAX_EMAIL_SINGLE`        | Maximum recipients per single email     | `3`          |

### **Redis Configuration**
| Variable        | Description        | Default Value |
|---------------|------------------|--------------|
| `REDIS_HOST`  | Redis server host  | `localhost` |
| `REDIS_PORT`  | Redis server port  | `6379`       |
| `REDIS_PASSWORD` | Redis password (if applicable) | `password_here` |

### **Socket Configuration**
| Variable        | Description         | Default Value |
|---------------|------------------|--------------|
| `SOCKET_HOST` | Milter socket host | `"localhost"` |
| `SOCKET_PORT` | Milter socket port | `10032` |

---

## Done
