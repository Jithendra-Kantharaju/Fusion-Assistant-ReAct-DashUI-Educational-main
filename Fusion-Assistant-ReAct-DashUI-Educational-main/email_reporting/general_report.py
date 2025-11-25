# fusion_assistant_ReAct/email_reporting/general_report.py
# Structured email template for asset/investigation reports.

GENERAL_REPORT_TEMPLATE = """\
Dear {recipient_name},

I am writing to provide you with the results of the recent investigation regarding {subject}.

---

### Summary of Findings
{findings}

### Root Cause
{root_cause}

### Impact Assessment
{impact_assessment}

### Corrective Actions Taken
{corrective_actions}

### Next Steps / Preventive Measures
{preventive_measures}

---

We take this matter very seriously and remain committed to ensuring the integrity and reliability of our operations.
Please let me know if you would like to schedule a meeting to review the findings in further detail.

Thank you for your attention to this matter.

Sincerely,
{sender_name}
{sender_title}
{sender_contact}
"""
