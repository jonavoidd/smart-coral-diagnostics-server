# Public Coral Bleaching Alert System Documentation

## Overview

The Public Coral Bleaching Alert System provides real-time bleaching alerts to all users without requiring authentication. This system automatically displays bleaching alerts when thresholds are reached, making coral conservation information accessible to the general public.

## Key Features

### 🌍 **Public Access**

- **No Authentication Required**: Anyone can view bleaching alerts
- **Real-time Updates**: Alerts are automatically created when thresholds are reached
- **Global Coverage**: Alerts from all monitored areas worldwide

### 📊 **Comprehensive Data**

- **Live Statistics**: Real-time bleaching case counts
- **Severity Classification**: Critical, High, Medium, Low severity levels
- **Geographic Information**: Location-based alert filtering
- **Historical Data**: Alert history and trends

### 🔄 **Automatic Updates**

- **Threshold Monitoring**: Automatically creates alerts when 200+ cases are detected
- **Real-time Sync**: Updates every 15 minutes via Celery tasks
- **Smart Deduplication**: Updates existing alerts instead of creating duplicates

## API Endpoints

### Public Endpoints (No Authentication Required)

#### Get All Public Alerts

```http
GET /api/v1/public/alerts
```

**Query Parameters:**

- `active_only` (boolean): Show only active alerts (default: true)
- `severity_level` (string): Filter by severity (critical, high, medium, low)
- `limit` (int): Number of alerts to return (max: 100, default: 50)
- `offset` (int): Number of alerts to skip (default: 0)

**Example Response:**

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "area_name": "Manila Bay, Philippines",
    "latitude": 14.5995,
    "longitude": 120.9842,
    "bleaching_count": 250,
    "threshold": 200,
    "severity_level": "high",
    "affected_radius_km": 50.0,
    "created_at": "2024-01-15T10:30:00Z",
    "last_updated": "2024-01-15T14:45:00Z",
    "is_active": true
  }
]
```

#### Get Alert Summary

```http
GET /api/v1/public/alerts/summary
```

**Response:**

```json
{
  "total_active_alerts": 15,
  "critical_alerts": 3,
  "high_alerts": 5,
  "medium_alerts": 4,
  "low_alerts": 3,
  "last_updated": "2024-01-15T14:45:00Z"
}
```

#### Get Public Statistics

```http
GET /api/v1/public/alerts/stats
```

**Response:**

```json
{
  "total_bleaching_cases_today": 45,
  "total_bleaching_cases_this_week": 320,
  "total_bleaching_cases_this_month": 1250,
  "most_affected_areas": [
    { "area": "Manila Bay, Philippines", "cases": 150 },
    { "area": "Great Barrier Reef, Australia", "cases": 89 }
  ],
  "severity_distribution": {
    "high": 25,
    "medium": 45,
    "low": 30
  },
  "last_updated": "2024-01-15T14:45:00Z"
}
```

#### Get Specific Alert

```http
GET /api/v1/public/alerts/{alert_id}
```

### Admin Endpoints (Authentication Required)

#### Create Public Alert

```http
POST /api/v1/public/admin/alerts
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "area_name": "Caribbean Sea",
  "latitude": 18.2208,
  "longitude": -66.5901,
  "bleaching_count": 180,
  "threshold": 200,
  "severity_level": "medium",
  "description": "High bleaching activity detected"
}
```

#### Update Public Alert

```http
PUT /api/v1/public/admin/alerts/{alert_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "bleaching_count": 220,
  "severity_level": "high",
  "is_active": true
}
```

#### Deactivate Public Alert

```http
DELETE /api/v1/public/admin/alerts/{alert_id}
Authorization: Bearer <admin_token>
```

## Database Schema

### Public Bleaching Alerts Table

```sql
CREATE TABLE public_bleaching_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    area_name VARCHAR(255) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    bleaching_count INTEGER NOT NULL,
    threshold INTEGER DEFAULT 200,
    severity_level VARCHAR(50) DEFAULT 'medium',
    affected_radius_km FLOAT DEFAULT 50.0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW()
);
```

### Public Alert History Table

```sql
CREATE TABLE public_alert_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    old_value VARCHAR(255),
    new_value VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## How It Works

### 1. Automatic Alert Creation

- **Celery Task**: `check_bleaching_thresholds` runs every 15 minutes
- **Threshold Detection**: Monitors for areas with 200+ bleaching cases
- **Public Alert Creation**: Automatically creates public alerts for display
- **Smart Updates**: Updates existing alerts instead of creating duplicates

### 2. Severity Classification

- **Critical**: 3x threshold or more (600+ cases)
- **High**: 2x threshold or more (400+ cases)
- **Medium**: 1.5x threshold or more (300+ cases)
- **Low**: At or above threshold (200+ cases)

### 3. Geographic Clustering

- **Location-based**: Alerts are grouped by geographic proximity
- **Radius Monitoring**: 50km default monitoring radius
- **Deduplication**: Prevents multiple alerts for the same area

## Frontend Integration

### React/JavaScript Example

```javascript
// Fetch all active alerts
const fetchPublicAlerts = async () => {
  const response = await fetch(
    "/api/v1/public/alerts?active_only=true&limit=20"
  );
  const alerts = await response.json();
  return alerts;
};

// Fetch alert summary
const fetchAlertSummary = async () => {
  const response = await fetch("/api/v1/public/alerts/summary");
  const summary = await response.json();
  return summary;
};

// Fetch statistics
const fetchAlertStats = async () => {
  const response = await fetch("/api/v1/public/alerts/stats");
  const stats = await response.json();
  return stats;
};
```

### Vue.js Example

```javascript
// Vue component for displaying alerts
export default {
  data() {
    return {
      alerts: [],
      summary: null,
      stats: null,
    };
  },
  async mounted() {
    await this.loadAlerts();
    await this.loadSummary();
    await this.loadStats();
  },
  methods: {
    async loadAlerts() {
      const response = await fetch("/api/v1/public/alerts");
      this.alerts = await response.json();
    },
    async loadSummary() {
      const response = await fetch("/api/v1/public/alerts/summary");
      this.summary = await response.json();
    },
    async loadStats() {
      const response = await fetch("/api/v1/public/alerts/stats");
      this.stats = await response.json();
    },
  },
};
```

## Mobile App Integration

### React Native Example

```javascript
// Fetch alerts for mobile app
const fetchAlertsForMobile = async () => {
  try {
    const response = await fetch("https://your-api.com/api/v1/public/alerts", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      const alerts = await response.json();
      return alerts;
    }
  } catch (error) {
    console.error("Error fetching alerts:", error);
  }
};
```

## Real-time Updates

### WebSocket Integration (Optional)

```javascript
// WebSocket connection for real-time updates
const ws = new WebSocket("ws://your-api.com/ws/public-alerts");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "alert_updated") {
    // Update UI with new alert data
    updateAlertDisplay(data.alert);
  }
};
```

## Caching Strategy

### Frontend Caching

```javascript
// Cache alerts for 5 minutes
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
let alertsCache = null;
let cacheTimestamp = null;

const getCachedAlerts = async () => {
  const now = Date.now();

  if (alertsCache && cacheTimestamp && now - cacheTimestamp < CACHE_DURATION) {
    return alertsCache;
  }

  const alerts = await fetchPublicAlerts();
  alertsCache = alerts;
  cacheTimestamp = now;

  return alerts;
};
```

## Performance Considerations

### Database Optimization

- **Indexes**: Proper indexing on latitude, longitude, severity_level, is_active
- **Pagination**: Limit results to prevent large data transfers
- **Caching**: Consider Redis caching for frequently accessed data

### API Rate Limiting

- **Public Endpoints**: 100 requests per minute per IP
- **Admin Endpoints**: 1000 requests per minute per authenticated user

## Security Considerations

### Public Data

- **No Sensitive Information**: Only display public bleaching data
- **Geographic Anonymity**: No specific user location data
- **Rate Limiting**: Prevent abuse of public endpoints

### Admin Access

- **Authentication Required**: All admin endpoints require valid tokens
- **Role-based Access**: Only admin users can create/modify alerts
- **Audit Trail**: All changes are logged in history table

## Monitoring and Analytics

### Key Metrics

- **Alert Creation Rate**: How many alerts are created per day
- **Public API Usage**: Number of requests to public endpoints
- **Geographic Distribution**: Which areas generate most alerts
- **Severity Trends**: How alert severity changes over time

### Health Checks

```http
GET /api/v1/public/health
```

**Response:**

```json
{
  "status": "healthy",
  "active_alerts": 15,
  "last_updated": "2024-01-15T14:45:00Z",
  "database_connected": true,
  "celery_worker_running": true
}
```

## Deployment

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/coral_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (for notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-app-password
```

### Docker Compose

```yaml
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/coral_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A app.core.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/coral_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A app.core.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/coral_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
```

## Usage Examples

### Public Dashboard

Create a public dashboard that shows:

- Current active alerts
- Alert severity distribution
- Geographic map of alerts
- Recent bleaching statistics

### Mobile App

Integrate alerts into mobile apps for:

- Push notifications for critical alerts
- Offline alert viewing
- Location-based alert filtering

### Conservation Organizations

Use the public API to:

- Display alerts on websites
- Create awareness campaigns
- Monitor global bleaching trends
- Generate reports for stakeholders

## Support and Maintenance

### Regular Tasks

- **Database Cleanup**: Remove old inactive alerts
- **Performance Monitoring**: Monitor API response times
- **Alert Validation**: Ensure alert accuracy
- **User Feedback**: Collect feedback on alert usefulness

### Troubleshooting

- **No Alerts Showing**: Check Celery worker status
- **Slow API Response**: Check database indexes
- **Missing Updates**: Verify Celery beat scheduler
- **High Memory Usage**: Monitor Redis cache size

This public alert system makes coral bleaching information accessible to everyone, promoting global awareness and conservation efforts! 🌊🐠
