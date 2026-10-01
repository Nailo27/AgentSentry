Sprint 1 Authorization Gateway

The gateway makes deterministic authorization decisions for synthetic
resources.

Protected resource:
  /restricted/payroll/payroll.csv

Roles:
  employee
  hr
  admin

Rules:
  - Public resources may be read by employee, hr, and admin.
  - Restricted payroll resources may only be read by hr or admin.
  - Employee requests for restricted payroll data are denied.
  - Unknown resources are denied.
  - Unsupported tool requests are denied.

Every gateway response must include:
  - decision: ALLOW or DENY
  - policy_id
  - human-readable reason

Required policy identifiers:
  POL-FILE-001      Authorized file read
  POL-FILE-004      Role lacks payroll access
  POL-RESOURCE-001  Unknown resource
  POL-INVALID-001   Unsupported tool request
