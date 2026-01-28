# ReadIn AI Backend

FastAPI backend server for ReadIn AI with PostgreSQL database and Stripe payment integration.

## Features

- User authentication (JWT tokens)
- Subscription management (Stripe)
- Usage tracking (daily limits for trial users)
- 7-day free trial with 10 responses/day
- $10/month premium plan with unlimited responses

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 13+
- Stripe account

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Or on Windows:
```bash
setup.bat
```

### 2. Set Up PostgreSQL

```bash
# Create database
createdb readin_ai

# Or using psql
psql -U postgres -c "CREATE DATABASE readin_ai;"
```

### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your settings
notepad .env  # Windows
nano .env     # Linux/Mac
```

Required settings:
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secure random string (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `STRIPE_SECRET_KEY` - From Stripe Dashboard
- `STRIPE_WEBHOOK_SECRET` - From Stripe Webhooks
- `STRIPE_PRICE_MONTHLY` - Created with setup_stripe.py

### 4. Initialize Database

```bash
python init_db.py
```

### 5. Set Up Stripe Products

```bash
python setup_stripe.py
```

This creates the subscription product and price in Stripe. Copy the price ID to your `.env` file.

### 6. Run the Server

```bash
# Development (with auto-reload)
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000

# Or on Windows
run.bat
```

Server runs at: http://localhost:8000

API Documentation: http://localhost:8000/docs

## Stripe Webhook Setup

1. Go to [Stripe Dashboard > Webhooks](https://dashboard.stripe.com/webhooks)
2. Add endpoint: `https://your-domain.com/webhooks/stripe`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy the webhook signing secret to `STRIPE_WEBHOOK_SECRET` in `.env`

## Docker Deployment

### Using Docker Compose

```bash
# Set environment variables
export DB_PASSWORD=your_secure_password
export JWT_SECRET=your_jwt_secret
export STRIPE_SECRET_KEY=sk_live_...
export STRIPE_WEBHOOK_SECRET=whsec_...
export STRIPE_PRICE_MONTHLY=price_...

# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
```

### Production with Nginx

```bash
# Start with nginx profile
docker-compose --profile production up -d
```

Make sure to:
1. Place SSL certificates in `./ssl/` directory
2. Update `nginx.conf` with your domain name
3. Point your domain DNS to the server

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create new account |
| POST | `/auth/login` | Login and get token |

### User

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/user/me` | Get user profile |
| GET | `/user/status` | Get subscription & usage status |

### Usage

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/usage/increment` | Track AI response usage |

### Subscription

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/subscription/create-checkout` | Get Stripe checkout URL |
| POST | `/subscription/manage` | Get billing portal URL |
| GET | `/subscription/status` | Get subscription details |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhooks/stripe` | Stripe webhook receiver |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

## Database Schema

### Users Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| email | String | Unique email |
| hashed_password | String | Bcrypt hash |
| full_name | String | Optional name |
| stripe_customer_id | String | Stripe customer ID |
| subscription_status | String | trial/active/cancelled/expired |
| subscription_id | String | Stripe subscription ID |
| trial_start_date | DateTime | Trial start |
| trial_end_date | DateTime | Trial end |

### Daily Usage Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to users |
| date | Date | Usage date |
| response_count | Integer | Responses used today |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection |
| `JWT_SECRET` | Yes | Token signing secret |
| `STRIPE_SECRET_KEY` | Yes | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Yes | Webhook signing secret |
| `STRIPE_PRICE_MONTHLY` | Yes | Monthly price ID |
| `TRIAL_DAYS` | No | Trial length (default: 7) |
| `TRIAL_DAILY_LIMIT` | No | Daily limit (default: 10) |

## Troubleshooting

### Database Connection Error

```
sqlalchemy.exc.OperationalError: could not connect to server
```

- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL format
- Check database exists: `psql -l`

### Stripe Authentication Error

```
stripe.error.AuthenticationError: Invalid API Key
```

- Verify STRIPE_SECRET_KEY in .env
- Check you're using the correct mode (test vs live)

### Webhook Signature Error

```
stripe.error.SignatureVerificationError
```

- Verify STRIPE_WEBHOOK_SECRET matches your endpoint
- Check the webhook URL is correct
- Ensure raw request body is being passed

## Security Notes

- Never commit `.env` file to version control
- Use strong, unique JWT_SECRET in production
- Enable HTTPS in production
- Rotate secrets periodically
- Monitor for suspicious activity
