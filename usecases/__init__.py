"""Registry of use cases. Each subpackage exposes a `render()` UI entry point."""

USE_CASES = [
    {
        "key": "sales_order",
        "number": 1,
        "title": "Automate Sales Order Entry",
        "icon": "📄",
        "tagline": "Extract POs from emails/documents → match master data → mock D365 order.",
        "status": "live",
    },
    {
        "key": "usecase2",
        "number": 2,
        "title": "Use Case 2",
        "icon": "🧩",
        "tagline": "Placeholder — to be defined.",
        "status": "planned",
    },
    {
        "key": "usecase3",
        "number": 3,
        "title": "Use Case 3",
        "icon": "🧩",
        "tagline": "Placeholder — to be defined.",
        "status": "planned",
    },
]
