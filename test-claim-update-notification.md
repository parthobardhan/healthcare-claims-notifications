# Testing Claim Update Notifications

## How to Test the Complete Flow

### 1. Patient Subscribes to Notifications
1. Go to the Patient Portal: http://localhost:4201/
2. Enter a **Member ID** (e.g., M123)
3. Enter an **Email** for notifications
4. Click **"Lookup Claims"** to see your claims
5. Click **"Subscribe to Push"** and allow notifications when prompted

### 2. Adjuster Updates a Claim
1. Go to the Adjuster Portal: http://localhost:4200/
2. Find a claim for the Member ID you used above
3. Click **"Edit"** on that claim
4. Change the **Status** (e.g., from "pending" to "paid")
5. Optionally add **Notes** (e.g., "Claim approved after review")
6. Click **OK** to save

### 3. Verify Notification Delivery
- The patient should receive a push notification immediately
- Check browser console for Service Worker logs
- Notification should be customized based on the new status

## Testing via API

You can also test programmatically:

```bash
# 1. Get a claim to update
CLAIM_ID=$(curl -s http://localhost:8080/claims | jq -r '.[0].id')
MEMBER_ID=$(curl -s http://localhost:8080/claims | jq -r '.[0].member_id')

# 2. Update the claim status
curl -X PATCH http://localhost:8080/claims/$CLAIM_ID \
  -H "Content-Type: application/json" \
  -d '{"status": "paid", "notes": "API test - claim approved"}'

# 3. Check the backend logs for notification delivery
```

## Expected Behavior

✅ **What should happen:**
1. Claims backend detects status change
2. Sends HTTP request to notification service with member_id
3. Notification service finds users subscribed for that member_id
4. Push notification sent to those users
5. Patient sees notification: "🏥 Healthcare Claim Update - Great news! Your claim has been approved and payment processed."

## Troubleshooting

If notifications don't work:
1. Check browser notification permissions
2. Verify patient subscribed with the correct member_id
3. Check browser console (F12) for errors
4. Look at backend logs for notification sending status
5. Try switching browser tabs (Chrome sometimes suppresses notifications on focused tabs)
