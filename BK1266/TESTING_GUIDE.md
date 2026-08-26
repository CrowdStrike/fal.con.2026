# 🔧 Testing Your Health Check App

## 🌐 Your Live App

After deploying, find your app URL in the Foundry App Manager under your tenant's deployed apps.

## ✅ Quick Test in Browser Console

### Method 1: Wait for Falcon SDK to Load

Open the page, press **F12** for DevTools console, and try:

```javascript
// Wait for the page to fully load, then try:
setTimeout(() => {
  // Access the global FalconApi instance
  const sdk = window.FalconApi || window.falcon;

  if (sdk) {
    sdk.api({
      path: '/api/health/check',
      method: 'POST',
      body: {}
    }).then(r => r.json()).then(d => {
      console.log('✅ Health Check Result:', d);
      console.log('Overall Score:', d.overall_score);
      console.log('Status:', d.overall_status);
    });
  } else {
    console.log('⚠️ Falcon SDK not loaded yet. Wait a few seconds and try again.');
  }
}, 3000);
```

### Method 2: Access from React DevTools

1. Install React DevTools extension
2. Open the page
3. Open React DevTools
4. Find the `Home` component
5. Inspect the `falcon` object in props/context

## 🐛 Debugging - Check What Happened

Open browser console and run:

```javascript
// Check if the page loaded
console.log('Page location:', window.location.href);

// Check for errors
console.log('Check for errors in Network tab');

// Look for the FalconApi
console.log('Window keys:', Object.keys(window).filter(k => k.toLowerCase().includes('falcon')));

// Check if React loaded
console.log('React loaded?', typeof React !== 'undefined');
```

## 🔍 Common Issues

### Issue 1: "falcon.api is not a function"
**Cause:** The Falcon SDK hasn't loaded yet
**Fix:** Wait 3-5 seconds after page load, then try again

### Issue 2: Empty/Blank Page
**Cause:** React build might have issues
**Fix:** Check browser console for errors

### Issue 3: "Failed to fetch health data"
**Possible causes:**
1. Function not deployed properly
2. OAuth scopes missing
3. Function has an error

**Debug:**
```javascript
// Check function directly
fetch(window.location.origin + '/api/health/check', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({})
})
.then(r => r.text())
.then(console.log)
.catch(console.error);
```

## 📊 What You Should See

If everything works, you should see:

1. **Dashboard loads** with empty cards
2. **Button appears**: "Run Health Check"
3. **Click button** → Spinner shows
4. **After 2-3 seconds**:
   - Overall score (0-100) with progress ring
   - Total policies count
   - Critical issues count
   - Timestamp
5. **Tabs appear**: Prevention, Response, Firewall
6. **Click tabs** → Policy tables display

## 🔧 Force React Rebuild

If the page isn't working, rebuild:

```bash
cd ui/pages/health-dashboard-react
npm install
npm run build
cd ../../..
FOUNDRY_FF_ENHANCED_UI=false foundry apps deploy --change-type patch --change-log "Rebuilt React UI"
```

## 📸 Manual Screenshot Guide

Since Playwright has certificate issues, just:

1. **Open the page** in Chrome
2. **Press Cmd+Shift+P** (Mac) or **Ctrl+Shift+P** (Windows)
3. **Type**: "screenshot"
4. **Choose**: "Capture full size screenshot"

This captures the entire page including scrollable content!

## ✅ Success Checklist

- [ ] Page loads without console errors
- [ ] "Run Health Check" button visible
- [ ] Clicking button shows spinner
- [ ] Health data appears after check
- [ ] Overall score displays with progress ring
- [ ] Tabs are clickable
- [ ] Policy tables show data

## 🚨 Still Having Issues?

Check the Foundry deployment logs in the Foundry App Manager under your tenant. Look for function errors in the logs.
