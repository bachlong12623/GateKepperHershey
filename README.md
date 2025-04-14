# GateKeeper Hershey - Scan Packout System

A PyQt5-based application for managing product scanning and packaging verification in a manufacturing environment.

## Features

- Work order verification
- Serial number scanning and validation
- Inner code verification 
- Real-time database integration
- Duplicate serial number detection
- Automated port detection for barcode scanners
- Password-protected override system
- Quality inspection tracking
- Live data monitoring

## System Requirements

- Python 3.6+
- PostgreSQL database
- Serial barcode scanner
- PyQt5
- psycopg2

## Configuration

The application uses a `config.ini` file for configuration settings:

```ini
[Database]
database_ip = your_database_ip
database_port = your_database_port
database_glovia = glovia_database_name
database_spk = spk_database_name
database_user = database_username
database_password = database_password

[Settings]
password = override_password
klippel_time = 4

[ModelName]
tray_quantity = number_of_items
```

## Usage Flow

1. **Date Selection**
   - Select date from calendar
   - Line selection becomes enabled

2. **Line Selection**
   - Choose production line
   - Model selection becomes enabled

3. **Model Selection**
   - Select product model
   - Shift selection becomes enabled
   - Tray quantity loaded from config

4. **Work Order Scanning**
   - Scan work order barcode
   - System validates against database
   - Shows OK/NG status

5. **Inner Code Processing**
   - Scan inner code twice for verification
   - System validates format and content
   - Shows remaining quantity

6. **Serial Number Scanning**
   - Scan product serial numbers
   - System verifies against work order
   - Checks for duplicates
   - Validates date codes
   - Updates database records

## Error Handling

- Duplicate serial detection with password override
- Date code mismatch warnings
- Database connection monitoring
- Invalid scan alerts
- Work order validation

## Database Integration

Connects to two databases:
- Glovia database: Work order information
- SPK database: Production and inspection data

## Tables

### i_packing
- id: Record ID
- date: Production date
- line: Production line
- model: Product model
- shift: Work shift
- inner_code: Container code
- serial: Product serial
- klippel: Test result
- result: Pass/Fail status
- scan_time: Timestamp

### i_packing_duplicate
- Stores information about duplicate scanned items
- Same structure as i_packing

## Maintenance

1. Regular database backup recommended
2. Monitor log files for errors
3. Update configuration as needed
4. Regular scanner calibration

## Troubleshooting

Common issues and solutions:
1. Scanner not detected
   - Check USB connection
   - Verify COM port settings

2. Database connection failed
   - Check network connectivity
   - Verify database credentials

3. Invalid serial numbers
   - Verify work order matches production line
   - Check date code format

## Security Features

- Password protection for duplicate overrides
- Shift-based access control
- Audit trail of all scans
- Database access restrictions

## Support

For technical support contact:
- System Administrator
- Database Administrator
- Production Support Team
