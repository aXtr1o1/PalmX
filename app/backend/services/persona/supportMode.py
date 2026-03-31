SUPPORT_MODES = {
    "re_engagement": {
        "objective": "Re-engage inactive user.",
        "rules": "Restart conversation naturally.",
        "do": "Use a hook or new value.",
        "dont": "Do not repeat previous content.",
        "output": "Re-engagement message."
    },

    "shortlist_refinement": {
        "objective": "Narrow down options.",
        "rules": "Ask preference-based question.",
        "do": "Help user choose.",
        "dont": "Do not introduce new options unnecessarily.",
        "output": "Refinement question."
    },

    "comparison": {
        "objective": "Compare multiple projects.",
        "rules": "Provide structured comparison.",
        "do": "Highlight key differences.",
        "dont": "Do not overwhelm with data.",
        "output": "Side-by-side comparison."
    },

    "faq": {
        "objective": "Answer direct factual questions.",
        "rules": "Be concise and accurate.",
        "do": "Provide direct answer.",
        "dont": "Do not oversell.",
        "output": "Clear factual response."
    },

    "detail_drilldown": {
        "objective": "Provide deep info on one project.",
        "rules": "Focus on one entity.",
        "do": "Give detailed breakdown.",
        "dont": "Do not switch topics.",
        "output": "Detailed explanation."
    }
}