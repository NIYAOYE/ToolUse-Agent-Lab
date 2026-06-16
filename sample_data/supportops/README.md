# SupportOps Sample Data

This folder contains synthetic tickets and attachments for local testing.

## Import Tickets

JSON import:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/tickets/import `
  -F "file=@sample_data/supportops/tickets.json"
```

CSV import:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/tickets/import `
  -F "file=@sample_data/supportops/tickets.csv"
```

## Upload Attachments

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/tickets/INC-2001/attachments `
  -F "file=@sample_data/supportops/attachments/INC-2001/orders-api.log;type=text/plain"
```

Attachment media types:

- `.log` and `.txt`: `text/plain`
- `.csv`: `text/csv`
- `.json`: `application/json`

These files are designed to exercise `log_scan`, `json_query`, and `csv_profile`.
