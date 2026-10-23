# Security Policy

## Supported Versions

AgentSentry is currently being developed for our CYBR 4580 Capstone Project at the University of Nebraska at Omaha. Since the project is still in development, security issues and fixes will be addressed in the most recent version.

| Version | Supported |
|---------|-----------|
| Current development version | Yes |
| Previous versions | No |

## Reporting a Vulnerability

If a security vulnerability is found within AgentSentry, it should privately reported to the project team so the issue can be properly investigated and addressed.

When you are reporting the vulnerability, please include the following information:

- A description of the security issue.
- Steps explaining how the issue can be reproduced.
- The files or components affected.
- The possible security risks or impact.
- Any screenshots, logs, or other evidence that can help explain the issue.

Security vulnerabilities should not be posted publicly on GitHub Issues until the project team has had an opportunity to investigate and address them.

## Security Expectations

AgentSentry is designed to test AI agents for security weaknesses, such as accessing restricted information, performing unauthorized actions, or going beyond their assigned permissions.

To help protect the system, the project follows these security expectations:

- **Access Control:** Users and AI agents should only be able to access information and resources allowed by their assigned roles.
- **Authorization:** The authorization gateway must check requests before allowing access to protected resources.
- **Sensitive Data:** Restricted information must not be exposed to unauthorized users or AI agents.
- **Logging:** Security tests and authorization decisions must be recorded so the team can determine what happened during a test.
- **Default Deny:** Requests with missing, invalid, or conflicting authorization information must be denied.
- **Testing Environment:** Security testing must be performed in approved environments using synthetic data instead of real sensitive information.

## Responsible Security Testing

AgentSentry is being developed for educational purposes and authorized security testing. All testing should be performed in a controlled environment to avoid affecting systems outside the project's scope.

Contributors should follow these guidelines:

- Only test systems that they own or have permission to assess.
- Use mock or synthetic data instead of real employee or company information.
- Do not include passwords, API keys, or other sensitive information in the repository.
- Avoid exposing protected information in logs, test results, or documentation.
- Report any discovered security issues to the project team.

## Security Updates

When a security issue is reported, the project team will investigate the issue and determine its potential impact. Issues that create a higher security risk should be addressed first.

Once a vulnerability has been fixed, the changes should be documented so the team can track what was updated and why.