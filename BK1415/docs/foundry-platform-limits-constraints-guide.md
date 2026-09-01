---
title: "Foundry Platform Limits & Constraints Guide"
confluence_space: "Javier Carrasco"
confluence_space_key: "~jcarrasco"
confluence_page_id: 689686278
confluence_url: "https://wiki.cs.sys/spaces/~jcarrasco/pages/689686278/Foundry+Platform+Limits+Constraints+Guide"
confluence_version: 1
last_modified: "2025-08-22T10:44:57.000Z"
last_modified_by: "Javier Carrasco"
pulled_at: "2026-02-13T19:59:54.000Z"
---

# Foundry Platform Limits & Constraints Guide

This guide is AI generated and not validated. It may contain errors

Function Limits
---------------

### Execution Limits

* **Default Timeout:** 30 seconds
* **Maximum Timeout:** 900 seconds (15 minutes) for all functions
* **Maximum Concurrent Executions:** 100 functions running simultaneously
* **Request Payload Size:** ~124KB maximum (128KB technical limit)
* **Response Payload Size:** ~120KB maximum (128KB technical limit)

### Package & Memory Limits

* **Package Size (Zipped):** 50MB maximum
* **Package Size (Unzipped):** 256MB maximum when deployed
* **Default Memory:** 256MB
* **Maximum Memory:** 1GB (configurable via `max_exec_memory_mb` in manifest.yml)

### How to Configure Function Limits

```
# In your manifest.yml
functions:
  - name: my-function
    max_exec_duration_seconds: 900   # 15 minutes max for all functions
    max_exec_memory_mb: 1024        # 1GB memory
```

### Function File System

* **Writable Directory:** Only `/tmp` is writable
* **File Operations:** Read-only access to function code, write access only to `/tmp`

Collection Limits
-----------------

### Size & Performance

* **Object Size:** Technically unlimited, but performance degrades with large objects
* **Recommended Object Size:** Keep under 80MB for good performance
* **Total Objects:** No hard limit, but performance impacts with very large datasets
* **Searchable Fields:** Maximum 10 fields can have `x-cs-indexable` flag

### Schema Constraints

* **Top-level Arrays:** Not supported when using schemas with indexable fields
* **Required Format:** Objects must be wrapped (use `{"items": [...]}` instead of `[...]`)

### Retention

* **Data Retention:** No automatic retention - objects persist until manually deleted
* **Best Practice:** Implement cleanup workflows for unused data

Query Limits
------------

### Concurrent Execution

* **Default Concurrent Queries:** 35 per user for `foundry_query` type
* **Maximum Concurrent Queries:** 50 per user (can be increased via support request)
* **Query Timeout:** 1 minute for saved search operations

### Query Constraints

* **Search Query Args:** 255 character limit (can cause timeout errors if exceeded)
* **Time Windows:** Large time windows (7+ days) may timeout on high-volume data

API Integration Limits
----------------------

### Request/Response Limits

* **Timeout:** 15 seconds (not configurable by users)
* **Response Types:** JSON only (no plain text, XML, or other formats in workflows)
* **Protocol Support:** HTTPS only (HTTP not supported for security)

### Authentication

* **OAuth Support:** Client Credentials flow only (no Authorization Code flow)
* **Certificate Validation:** Required (cannot bypass SSL validation for cloud APIs)

Workflow Limits
---------------

### Execution Constraints

* **Concurrent Loops:** Processed in batches of 500 iterations
* **Schema Requirements:** Root elements must be objects, not arrays
* **Variable Names:** Must be unique across the entire CID
* **Parameterized Fields:** Limited support in certain contexts (like loops)

UI Extension & Page Limits
--------------------------

### Development Constraints

* **Creation Method:** UI Extensions can only be created via CLI (no UI creation)
* **Supported Operations:** GET operations only (no POST operations currently)
* **Socket Availability:** Limited to specific UI locations (not all pages support extensions)

### Content Security Policy

* **External Resources:** Must be explicitly allowed in manifest CSP settings
* **Supported Directives:** connect-src, style-src, style-src-elem, script-src, form-action, img-src, media-src, object-src

App-Level Limits
----------------

### Deployment & Management

* **Apps per CID:** Varies by subscription tier
  + Free tier: 1 app
  + Paid tiers: Based on data ingestion volume
* **Cross-CID Support:** None - apps are CID-specific
* **Flight Control:** Not supported - must install separately in each CID

### Naming Constraints

* **App Names:** 1-50 characters
* **Workflow Names:** Must be unique across entire CID
* **Artifact IDs:** Must be unique across all apps in CID

RTR Script Limits
-----------------

### Execution Environment

* **Platform Support:** Windows, Linux, and macOS platforms
* **Execution Context:** Runs directly on remote endpoints through Falcon's Real Time Response service
* **MFA Requirements:** CLI releases do not trigger MFA identity verification for RTR capabilities (only UI releases do)

### Management Constraints

* **Deletion Requirements:** Falcon Administrator role required to delete RTR scripts
* **Deletion Method:** RTR scripts must be deleted through the UI (not CLI)
* **Dependency Management:** Scripts in use cannot be deleted until dependencies are resolved

Developer CID Limits
--------------------

### Subscription Exclusions

Developer CIDs exclude these product subscriptions:

* Falcon Complete
* Falcon Data Replicator
* Falcon Flight Control
* Falcon Forensics
* Falcon Overwatch
* IoT (Discovery for IoT)

### Access Requirements

* **Falcon Administrator:** Can request and access a developer CID
* **Foundry Developer:** Can access a developer CID
* **Required Subscriptions:** Falcon Foundry Development, Falcon Foundry Mocks Generator

App Documentation Limits
------------------------

### File Constraints

* **Maximum Image Size:** 5 MB per image
* **Supported Image Types:** JPG and PNG only
* **Filename Requirements:** Only alphanumeric filenames supported
* **File Replacement:** Identical filenames replace existing files

### Content Limitations

* **Image Support:** Basic markdown images only (no HTML img tags with width control)
* **Folder Structure:** Sub-folders in app\_docs not officially supported
* **File Organization:** Keep all assets in same directory as README.md

Release Management
------------------

### Release Types

* **Minor and Patch Releases:** Updated in catalog automatically
* **Major Releases:** Must be accepted manually
* **MFA Requirements:** CLI releases do not trigger MFA for RTR capabilities (UI releases do)

### Retry Capabilities

* Failed releases can be retried from the App details page
* Re-release option available from both main page and Releases tab

LogScale Integration Limits
---------------------------

### Repository Access

* **Data Views:** Limited to specific repositories based on app configuration
* **Retention Period:** Same as your Falcon subscription retention period
* **Query Complexity:** Complex queries may timeout during LogScale maintenance

Network & Security Limits
-------------------------

### IP Restrictions

* **Outbound IPs:** Fixed set of egress IPs (see documentation for current list)
* **Inbound Access:** API integrations cannot use IP addresses as hosts
* **Certificate Requirements:** Valid SSL certificates required for all external connections

Storage Limits
--------------

### Code Storage

* **Per-CID Limit:** Varies by environment (can hit `CodeStorageExceededException`)
* **Cleanup:** Deleting unused apps frees up storage space
* **Versioning:** Each deployment creates a new version consuming storage

Performance Guidelines
----------------------

### Best Practices for Large Data

* **Functions:** Break large processing into smaller chunks
* **Collections:** Use pagination for large datasets
* **Queries:** Optimize time windows and filters
* **UI:** Implement virtualization for >500 records

### Recommended Thresholds

* **Function Response:** Keep under 100KB for best performance
* **Collection Objects:** Keep under 10MB per object
* **Query Results:** Limit to reasonable result sets to avoid timeouts
* **UI Rendering:** Paginate or virtualize lists over 500 items

Workarounds for Common Limits
-----------------------------

### Large Data Processing

```
# Instead of processing 100MB in one function:
# 1. Split into smaller chunks
# 2. Use multiple function calls
# 3. Store intermediate results in collections
# 4. Use workflows to orchestrate the process
```

### Extended Timeouts

```
# Increase function timeout in manifest.yml
functions:
  - name: long-running-function
    max_exec_duration_seconds: 900  # 15 minutes
```

### Large Response Handling

```
# Store large data in collections, return references
def my_function(request):
    large_data = process_data()
    
    # Store in collection
    collection_client.store_object(key="result_123", data=large_data)
    
    # Return reference instead of data
    return {"result_key": "result_123", "status": "complete"}
```

Getting Limit Increases
-----------------------

### What Can Be Increased

* Concurrent query limits (contact #ask-cs-jobs)
* Code storage limits (contact support)
* Function memory allocation (up to 1GB)
* Function timeout (up to 15 minutes for all functions)

### What Cannot Be Increased

* Request/response payload sizes (128KB hard limit)
* API integration timeouts (15 seconds fixed)
* Cross-CID functionality (architectural limitation)

Monitoring Your Usage
---------------------

### Check Your Limits

* **Function Executions:** Monitor concurrent usage in workflows
* **Storage Usage:** Track through deployment errors
* **Query Usage:** Monitor concurrent query errors
* **Collection Size:** Implement size tracking in your apps

### Warning Signs

* `CodeStorageExceededException` errors
* "Max number of running jobs" errors
* Function timeout errors increasing
* Collection performance degrading

Planning for Scale
------------------

### Architecture Considerations

* Design for the 128KB payload limit from the start
* Plan data processing workflows for large datasets
* Implement proper error handling for limit scenarios
* Use collections for persistent data storage
* Consider external processing for ML/heavy compute workloads

Remember: These limits exist to ensure platform stability and performance. Design your applications with these constraints in mind rather than trying to work around them.