# Next.js WebSocket Integration for Real-time Alerts

## Overview

This guide shows how to integrate real-time coral bleaching alerts into your Next.js frontend application using WebSocket connections.

## WebSocket Endpoints

### Alert Notifications

```
ws://localhost:8000/api/v1/ws/ws/alerts
```

### General Notifications (Stats, etc.)

```
ws://localhost:8000/api/v1/ws/ws/general
```

## React Hook for WebSocket Connection

### `useWebSocketAlerts.js`

```javascript
import { useState, useEffect, useRef } from "react";

export const useWebSocketAlerts = (url) => {
  const [alerts, setAlerts] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = () => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case "connected":
            console.log("Connected to alert notifications");
            break;

          case "new_alert":
            console.log("New alert received:", data.data);
            setAlerts((prev) => [data.data, ...prev]);
            // Show browser notification
            if (Notification.permission === "granted") {
              new Notification("🚨 New Coral Bleaching Alert", {
                body: `Alert in ${data.data.area_name}: ${data.data.bleaching_count} cases detected`,
                icon: "/coral-icon.png",
              });
            }
            break;

          case "alert_updated":
            console.log("Alert updated:", data.data);
            setAlerts((prev) =>
              prev.map((alert) =>
                alert.id === data.data.id ? data.data : alert
              )
            );
            break;

          case "stats_updated":
            console.log("Stats updated:", data.data);
            // Handle stats updates if needed
            break;

          case "pong":
            // Keepalive response
            break;

          default:
            console.log("Unknown message type:", data.type);
        }
      };

      ws.current.onclose = () => {
        console.log("WebSocket disconnected");
        setIsConnected(false);

        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          const delay = Math.pow(2, reconnectAttempts.current) * 1000; // Exponential backoff
          console.log(
            `Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setError("Failed to reconnect after multiple attempts");
        }
      };

      ws.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        setError("WebSocket connection error");
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
      setError("Failed to create WebSocket connection");
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (ws.current) {
      ws.current.close();
    }
  };

  const sendPing = () => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "ping" }));
    }
  };

  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [url]);

  // Send ping every 30 seconds to keep connection alive
  useEffect(() => {
    if (isConnected) {
      const pingInterval = setInterval(sendPing, 30000);
      return () => clearInterval(pingInterval);
    }
  }, [isConnected]);

  return {
    alerts,
    isConnected,
    error,
    reconnect: connect,
  };
};
```

## React Component for Real-time Alerts

### `RealTimeAlerts.jsx`

```jsx
import React, { useState, useEffect } from "react";
import { useWebSocketAlerts } from "./useWebSocketAlerts";

const RealTimeAlerts = () => {
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const { alerts, isConnected, error, reconnect } = useWebSocketAlerts(
    "ws://localhost:8000/api/v1/ws/ws/alerts"
  );

  // Request notification permission
  useEffect(() => {
    if ("Notification" in window) {
      Notification.requestPermission().then((permission) => {
        setNotificationsEnabled(permission === "granted");
      });
    }
  }, []);

  const getSeverityColor = (severity) => {
    switch (severity) {
      case "critical":
        return "bg-red-600";
      case "high":
        return "bg-orange-500";
      case "medium":
        return "bg-yellow-500";
      case "low":
        return "bg-green-500";
      default:
        return "bg-gray-500";
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case "critical":
        return "🚨";
      case "high":
        return "⚠️";
      case "medium":
        return "⚡";
      case "low":
        return "ℹ️";
      default:
        return "📊";
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Real-time Coral Bleaching Alerts
        </h1>

        <div className="flex items-center gap-4">
          <div
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              isConnected
                ? "bg-green-100 text-green-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            {isConnected ? "🟢 Connected" : "🔴 Disconnected"}
          </div>

          {error && (
            <div className="text-red-600 text-sm">
              {error}
              <button
                onClick={reconnect}
                className="ml-2 text-blue-600 hover:text-blue-800 underline"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg">
            {isConnected
              ? "No active alerts at the moment"
              : "Connecting to alert system..."}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`border-l-4 ${getSeverityColor(
                alert.severity_level
              )} bg-white shadow-md rounded-lg p-6`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">
                      {getSeverityIcon(alert.severity_level)}
                    </span>
                    <h3 className="text-xl font-semibold text-gray-900">
                      {alert.area_name}
                    </h3>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium uppercase ${getSeverityColor(
                        alert.severity_level
                      )} text-white`}
                    >
                      {alert.severity_level}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">Cases:</span>{" "}
                      {alert.bleaching_count}
                    </div>
                    <div>
                      <span className="font-medium">Threshold:</span>{" "}
                      {alert.threshold}
                    </div>
                    <div>
                      <span className="font-medium">Radius:</span>{" "}
                      {alert.affected_radius_km}km
                    </div>
                    <div>
                      <span className="font-medium">Updated:</span>{" "}
                      {new Date(alert.last_updated).toLocaleString()}
                    </div>
                  </div>

                  <div className="mt-3 text-sm text-gray-500">
                    📍 {alert.latitude.toFixed(4)}, {alert.longitude.toFixed(4)}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {notificationsEnabled && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-center gap-2 text-blue-800">
            <span>🔔</span>
            <span className="text-sm">Browser notifications are enabled</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default RealTimeAlerts;
```

## Next.js API Route for WebSocket Proxy (Optional)

### `pages/api/websocket-proxy.js`

```javascript
// Optional: If you need to proxy WebSocket connections
export default function handler(req, res) {
  // This is just a placeholder - WebSocket connections should be direct
  res.status(200).json({
    message:
      "Use direct WebSocket connection to ws://localhost:8000/api/v1/ws/ws/alerts",
  });
}
```

## App Integration

### `pages/_app.js`

```jsx
import { useEffect } from "react";
import { useRouter } from "next/router";

export default function App({ Component, pageProps }) {
  const router = useRouter();

  useEffect(() => {
    // Request notification permission on app load
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  return <Component {...pageProps} />;
}
```

### `pages/index.js`

```jsx
import RealTimeAlerts from "../components/RealTimeAlerts";

export default function Home() {
  return (
    <div>
      <RealTimeAlerts />
    </div>
  );
}
```

## Environment Configuration

### `.env.local`

```env
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000/api/v1/ws/ws/alerts
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Advanced Features

### Custom Hook with Caching

```javascript
import { useState, useEffect, useRef } from "react";

export const useWebSocketAlertsWithCache = (url) => {
  const [alerts, setAlerts] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const cacheRef = useRef(new Map());

  // ... WebSocket connection logic ...

  const addAlert = (alert) => {
    setAlerts((prev) => {
      const newAlerts = [alert, ...prev.filter((a) => a.id !== alert.id)];
      // Keep only last 100 alerts in memory
      return newAlerts.slice(0, 100);
    });

    // Cache the alert
    cacheRef.current.set(alert.id, alert);
  };

  const updateAlert = (alert) => {
    setAlerts((prev) => prev.map((a) => (a.id === alert.id ? alert : a)));

    // Update cache
    cacheRef.current.set(alert.id, alert);
  };

  // ... rest of the implementation
};
```

## Testing the Integration

### Test WebSocket Connection

```javascript
// Test script to verify WebSocket connection
const testWebSocket = () => {
  const ws = new WebSocket("ws://localhost:8000/api/v1/ws/ws/alerts");

  ws.onopen = () => {
    console.log("✅ WebSocket connected successfully");
    ws.send(JSON.stringify({ type: "ping" }));
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("📨 Received message:", data);
  };

  ws.onerror = (error) => {
    console.error("❌ WebSocket error:", error);
  };

  ws.onclose = () => {
    console.log("🔌 WebSocket closed");
  };
};

// Run test
testWebSocket();
```

## Production Considerations

### 1. WebSocket URL Configuration

```javascript
// utils/websocket.js
const getWebSocketUrl = () => {
  if (process.env.NODE_ENV === "production") {
    return "wss://your-api-domain.com/api/v1/ws/ws/alerts";
  }
  return "ws://localhost:8000/api/v1/ws/ws/alerts";
};
```

### 2. Error Handling

```javascript
const handleWebSocketError = (error) => {
  console.error("WebSocket error:", error);

  // Show user-friendly error message
  toast.error("Connection to alert system lost. Retrying...");

  // Log error for monitoring
  if (process.env.NODE_ENV === "production") {
    // Send to error tracking service
    console.error("WebSocket error:", error);
  }
};
```

### 3. Performance Optimization

```javascript
// Throttle rapid updates
const throttledUpdate = useCallback(
  throttle((alert) => {
    setAlerts((prev) => [alert, ...prev]);
  }, 1000),
  []
);
```

## Summary

With this implementation:

✅ **Automatic Real-time Notifications**: Your Next.js app will receive instant alerts when bleaching thresholds are reached

✅ **WebSocket Connection**: Persistent connection for real-time updates

✅ **Browser Notifications**: Native browser notifications for critical alerts

✅ **Auto-reconnection**: Automatic reconnection with exponential backoff

✅ **Error Handling**: Robust error handling and user feedback

✅ **Performance**: Optimized for production use

The system now provides **both email alerts** (for subscribed users) and **real-time WebSocket notifications** (for your Next.js frontend) whenever bleaching conditions are met! 🌊🐠📱
