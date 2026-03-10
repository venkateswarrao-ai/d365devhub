#!/usr/bin/env python3
"""
D365 Dev Hub — Auto Lesson Generator
Runs every alternate day via GitHub Actions.
Calls Claude API to generate a new D365 F&O lesson and appends it to site/data/lessons.json
"""

import os, sys, json, re, datetime, random, anthropic

# ─────────────────────────────────────────────────────────────────────────────
# TOPIC POOL — Claude picks the next topic not yet covered
# Add more topics here as the site grows
# ─────────────────────────────────────────────────────────────────────────────
TOPIC_POOL = [
    # X++ Language Deep Dives
    {"id": "xpp_display_methods",   "title": "Display & Edit Methods in X++",         "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_delegates",         "title": "Delegates & Event-Driven X++",           "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_crosscompany",      "title": "Cross-Company Queries in X++",           "section": "X++ Language",    "level": "Expert"},
    {"id": "xpp_containers",        "title": "Containers: Pack, Unpack & Serialize",   "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_reflection",        "title": "Reflection: DictTable, DictField APIs",  "section": "X++ Language",    "level": "Expert"},
    {"id": "xpp_runbase",           "title": "RunBase & RunBaseBatch Framework",       "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_sysoperation",      "title": "SysOperation Framework Deep Dive",       "section": "X++ Language",    "level": "Expert"},
    {"id": "xpp_dialogs",           "title": "Dialogs: Dialog, DialogField, Lookups",  "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_maps",              "title": "Table Maps & Map Extensions",             "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_global_class",      "title": "Global Class & Utility Methods",         "section": "X++ Language",    "level": "Beginner"},
    {"id": "xpp_label_files",       "title": "Label Files & Multi-Language Support",   "section": "X++ Language",    "level": "Beginner"},
    {"id": "xpp_edt_base",          "title": "EDTs: Inheritance, Relations, Lookups",  "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_postload",          "title": "postLoad, initValue & modifiedField",    "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_insert_update",     "title": "insert_recordset & update_recordset",    "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_delete_from",       "title": "delete_from & Bulk Operations",          "section": "X++ Language",    "level": "Intermediate"},
    {"id": "xpp_optimistic_concur", "title": "Optimistic Concurrency & Retry Logic",  "section": "X++ Language",    "level": "Expert"},

    # Extensions & AOT
    {"id": "ext_table_extension",   "title": "Table Extensions: Add Fields & Indexes", "section": "Extensions",     "level": "Intermediate"},
    {"id": "ext_form_datasource",   "title": "Form DataSource Extensions & Override",  "section": "Extensions",     "level": "Intermediate"},
    {"id": "ext_menu_items",        "title": "Menu Items, Menus & Action Pane Extensions","section":"Extensions",   "level": "Intermediate"},
    {"id": "ext_enum_extension",    "title": "Enum Extensions: Add Values Safely",     "section": "Extensions",     "level": "Beginner"},
    {"id": "ext_query_extension",   "title": "Query Extensions & Data Range Filters",  "section": "Extensions",     "level": "Intermediate"},
    {"id": "ext_ssrs_extension",    "title": "SSRS Report Extensions & DP Override",   "section": "Extensions",     "level": "Expert"},
    {"id": "ext_lookup_override",   "title": "Custom Lookups via FormControl Extensions","section":"Extensions",    "level": "Intermediate"},
    {"id": "ext_business_event",    "title": "Business Events: Custom & OOB",          "section": "Extensions",     "level": "Expert"},

    # Data Management
    {"id": "data_dixf_entities",    "title": "DIXF Custom Data Entities",             "section": "Data Model",      "level": "Expert"},
    {"id": "data_composite_entity", "title": "Composite Data Entities",               "section": "Data Model",      "level": "Expert"},
    {"id": "data_odata_filter",     "title": "OData Filtering, Expand & Metadata",   "section": "Data Model",      "level": "Expert"},
    {"id": "data_recurring_batch",  "title": "Recurring Integrations via DIXF API",  "section": "Data Model",      "level": "Expert"},
    {"id": "data_entity_events",    "title": "Data Entity Events & Staging Tables",  "section": "Data Model",      "level": "Expert"},

    # Finance & Accounting
    {"id": "fin_voucher_framework", "title": "Voucher Framework & Ledger Posting",   "section": "Finance",         "level": "Expert"},
    {"id": "fin_subledger",         "title": "Subledger Journal & AccountingEngine",  "section": "Finance",         "level": "Expert"},
    {"id": "fin_tax_engine",        "title": "GTE Tax Engine Configuration & X++",   "section": "Finance",         "level": "Expert"},
    {"id": "fin_bank_reconcile",    "title": "Bank Reconciliation Automation",        "section": "Finance",         "level": "Expert"},
    {"id": "fin_budget_control",    "title": "Budget Control & Encumbrance X++",     "section": "Finance",         "level": "Expert"},
    {"id": "fin_fixed_assets",      "title": "Fixed Assets Posting & Depreciation",  "section": "Finance",         "level": "Expert"},
    {"id": "fin_currency_reval",    "title": "Currency Revaluation via X++",          "section": "Finance",         "level": "Expert"},

    # Integration & Azure
    {"id": "int_service_bus",       "title": "Azure Service Bus: Publish & Subscribe","section": "Integrations",   "level": "Expert"},
    {"id": "int_logic_apps_adv",    "title": "Logic Apps: Error Handling & Retry",   "section": "Integrations",    "level": "Expert"},
    {"id": "int_power_automate",    "title": "Power Automate + D365 F&O Connectors", "section": "Integrations",    "level": "Intermediate"},
    {"id": "int_dataverse_link",    "title": "Dataverse Link & Virtual Tables",      "section": "Integrations",    "level": "Expert"},
    {"id": "int_azure_data_lake",   "title": "Azure Data Lake Export (BYOD/FnO)",    "section": "Integrations",    "level": "Expert"},
    {"id": "int_webhooks",          "title": "Webhooks from D365 via Business Events","section": "Integrations",   "level": "Expert"},
    {"id": "int_oauth_d365",        "title": "OAuth 2.0 & Service-to-Service Auth",  "section": "Integrations",    "level": "Expert"},

    # Performance & Architecture
    {"id": "perf_query_optimize",   "title": "Query Optimization: Indexes & Plans",  "section": "Architecture",    "level": "Expert"},
    {"id": "perf_set_based",        "title": "Set-Based vs Row-Based Operations",     "section": "Architecture",    "level": "Expert"},
    {"id": "perf_caching",          "title": "Table Caching: EntireTable vs Found",   "section": "Architecture",    "level": "Expert"},
    {"id": "perf_async_batch",      "title": "Async Processing & Task Parallelism",   "section": "Architecture",    "level": "Expert"},
    {"id": "arch_isv_design",       "title": "ISV Solution Design & AppSource",       "section": "Architecture",    "level": "Expert"},
    {"id": "arch_alm_pipeline",     "title": "Azure DevOps ALM for D365 F&O",        "section": "Architecture",    "level": "Expert"},
    {"id": "arch_multi_env",        "title": "Multi-Environment Strategy (DEV/UAT/PROD)","section":"Architecture",  "level": "Expert"},
    {"id": "arch_lcs_lifecycle",    "title": "LCS: Lifecycle Services Deep Dive",     "section": "Architecture",    "level": "Expert"},

    # Agentic AI
    {"id": "ai_langchain_d365",     "title": "LangChain Agents with D365 OData",     "section": "Agentic AI",      "level": "Expert"},
    {"id": "ai_rag_xpp",            "title": "RAG Pipeline for X++ Code Assistant",  "section": "Agentic AI",      "level": "Expert"},
    {"id": "ai_copilot_extend",     "title": "Extending M365 Copilot for D365",      "section": "Agentic AI",      "level": "Expert"},
    {"id": "ai_azure_openai_d365",  "title": "Azure OpenAI + D365 F&O Integration",  "section": "Agentic AI",      "level": "Expert"},
    {"id": "ai_prompt_engineering", "title": "Prompt Engineering for ERP Developers","section": "Agentic AI",      "level": "Intermediate"},
    {"id": "ai_teams_bot_d365",     "title": "Teams Bot Querying D365 via MCP",      "section": "Agentic AI",      "level": "Expert"},

    # Security & Compliance
    {"id": "sec_roles_duties",      "title": "Security Roles, Duties & Privileges",  "section": "Security",        "level": "Intermediate"},
    {"id": "sec_xds_policies",      "title": "XDS Policies & Row-Level Security",    "section": "Security",        "level": "Expert"},
    {"id": "sec_audit_trail",       "title": "Database Logging & Audit Trail",       "section": "Security",        "level": "Intermediate"},
    {"id": "sec_data_encryption",   "title": "Sensitive Field Encryption in D365",   "section": "Security",        "level": "Expert"},

    # Reporting
    {"id": "rep_er_framework",      "title": "Electronic Reporting (ER) Framework",  "section": "Reporting",       "level": "Expert"},
    {"id": "rep_financial_reports", "title": "Financial Reporting (Management Reporter)","section":"Reporting",     "level": "Intermediate"},
    {"id": "rep_power_bi_d365",     "title": "Power BI Embedded in D365 F&O",        "section": "Reporting",       "level": "Intermediate"},
    {"id": "rep_ssrs_rdl",          "title": "SSRS RDL Design & Report DP Class",    "section": "Reporting",       "level": "Expert"},
]

# ─────────────────────────────────────────────────────────────────────────────
# LESSON CONTENT TEMPLATE — what Claude must produce
# ─────────────────────────────────────────────────────────────────────────────
LESSON_SYSTEM_PROMPT = """You are a senior D365 F&O (Finance & Operations) developer with 15+ years of experience.
You write deeply technical, production-grade educational content for intermediate-to-expert D365 developers.

Your content must:
- Use real X++ code snippets (AOT-correct, compilable patterns)
- Reference real D365 F&O classes, tables, and AOT objects
- Explain WHY, not just HOW (design decisions, best practices)
- Include gotchas, anti-patterns, and performance tips
- Be structured for developers who already know C#/Java basics

Output ONLY valid JSON. No markdown, no explanation, no preamble."""

def build_lesson_prompt(topic, existing_ids):
    return f"""Generate a comprehensive D365 F&O lesson on this topic:

Topic ID: {topic['id']}
Title: {topic['title']}
Section: {topic['section']}
Level: {topic['level']}

Return a JSON object with EXACTLY this structure:
{{
  "id": "{topic['id']}",
  "title": "{topic['title']}",
  "section": "{topic['section']}",
  "level": "{topic['level']}",
  "duration": "XX min read",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "One sentence summary of what this lesson covers.",
  "content": {{
    "overview": "2-3 paragraph overview explaining the concept, why it matters, and when to use it in D365 F&O projects.",
    "theory": "Deep technical explanation with D365 architecture context. Reference specific AOT objects, classes, frameworks.",
    "code_examples": [
      {{
        "title": "Example title",
        "description": "What this code demonstrates",
        "language": "xpp",
        "code": "// Full compilable X++ code here\\nstatic void main(Args _args)\\n{{\\n    // Real code...\\n}}"
      }},
      {{
        "title": "Second example title",
        "description": "Advanced usage or variation",
        "language": "xpp",
        "code": "// Second code block"
      }}
    ],
    "key_points": [
      "Key takeaway 1 — specific and actionable",
      "Key takeaway 2",
      "Key takeaway 3",
      "Key takeaway 4",
      "Key takeaway 5"
    ],
    "gotchas": [
      "Common mistake 1 — explain WHY it's wrong and what to do instead",
      "Common mistake 2",
      "Common mistake 3"
    ],
    "performance_tips": [
      "Performance consideration 1",
      "Performance consideration 2"
    ],
    "related_topics": ["topic_id_1", "topic_id_2"],
    "quiz": [
      {{
        "q": "Question about this topic?",
        "options": ["Wrong answer A", "Correct answer B", "Wrong answer C", "Wrong answer D"],
        "answer": 1,
        "explanation": "Why B is correct: detailed explanation."
      }},
      {{
        "q": "Second question?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": 0,
        "explanation": "Why A is correct."
      }},
      {{
        "q": "Third question?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": 2,
        "explanation": "Why C is correct."
      }}
    ]
  }},
  "generated_date": "{datetime.date.today().isoformat()}",
  "auto_generated": true
}}

Make the code examples REAL and PRODUCTION-GRADE. Use proper X++ syntax with:
- Correct AOT object references
- Error handling with try/catch
- ttsbegin/ttscommit where relevant
- info() messages for demonstration
- Realistic field names from Contoso demo data

Existing lesson IDs to avoid duplicating: {existing_ids[:20]}"""

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Load existing lessons
    lessons_path = 'site/data/lessons.json'
    existing = []
    if os.path.exists(lessons_path):
        with open(lessons_path) as f:
            existing = json.load(f)
    
    existing_ids = [l['id'] for l in existing]
    print(f"📚 Existing lessons: {len(existing_ids)}")

    # Load topic rotation tracker
    tracker_path = 'site/data/topic_tracker.json'
    tracker = {'last_index': -1, 'completed': []}
    if os.path.exists(tracker_path):
        with open(tracker_path) as f:
            tracker = json.load(f)

    # Pick next topic not yet done
    available = [t for t in TOPIC_POOL if t['id'] not in tracker['completed'] and t['id'] not in existing_ids]
    
    if not available:
        print("✅ All topics covered! Resetting rotation...")
        tracker['completed'] = []
        available = TOPIC_POOL[:]

    # Pick next in sequence (or random if you prefer)
    topic = available[0]
    print(f"🎯 Generating lesson: {topic['title']}")

    # Call Claude API
    client = anthropic.Anthropic(api_key=api_key)
    
    print("🤖 Calling Claude API...")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=LESSON_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_lesson_prompt(topic, existing_ids)}
        ]
    )

    raw = message.content[0].text.strip()
    
    # Clean JSON (remove markdown fences if present)
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    # Parse and validate
    lesson = json.loads(raw)
    print(f"✅ Lesson generated: {lesson['title']}")

    # Append to lessons array
    existing.append(lesson)
    
    # Save lessons.json
    os.makedirs('site/data', exist_ok=True)
    with open(lessons_path, 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved to {lessons_path} ({len(existing)} total lessons)")

    # Update tracker
    tracker['completed'].append(topic['id'])
    tracker['last_index'] = TOPIC_POOL.index(topic)
    tracker['last_run'] = datetime.date.today().isoformat()
    tracker['last_title'] = lesson['title']
    with open(tracker_path, 'w') as f:
        json.dump(tracker, f, indent=2)

    # Save latest title for git commit message
    with open('site/data/latest_lesson_title.txt', 'w') as f:
        f.write(lesson['title'])

    # Update changelog
    changelog_path = 'site/data/changelog.json'
    changelog = []
    if os.path.exists(changelog_path):
        with open(changelog_path) as f:
            changelog = json.load(f)
    
    changelog.insert(0, {
        "date": datetime.date.today().strftime('%b %d'),
        "tag": "LESSON",
        "title": lesson['title'],
        "section": lesson['section'],
        "level": lesson['level'],
        "id": lesson['id']
    })
    changelog = changelog[:30]  # keep last 30
    with open(changelog_path, 'w') as f:
        json.dump(changelog, f, indent=2)

    print(f"\n🎉 Done! '{lesson['title']}' published.")
    print(f"📊 Total lessons: {len(existing)}")

if __name__ == '__main__':
    main()
