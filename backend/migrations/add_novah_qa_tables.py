#!/usr/bin/env python3
"""
Migration: Add Novah AI and QA tables

Adds:
- chat_sessions columns: is_ai_handled, ai_transferred_at, ai_resolution_status
- knowledge_base_articles table
- chat_qa_records table

Usage: python migrations/add_novah_qa_tables.py
"""

import sys
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "readin_ai.db"


def migrate():
    """Run the migration."""
    print("Adding Novah AI and QA tables...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check and add chat_sessions columns
        cursor.execute("PRAGMA table_info(chat_sessions)")
        columns = [col[1] for col in cursor.fetchall()]

        if "is_ai_handled" not in columns:
            cursor.execute("ALTER TABLE chat_sessions ADD COLUMN is_ai_handled BOOLEAN DEFAULT 1")
            print("  Added is_ai_handled column")

        if "ai_transferred_at" not in columns:
            cursor.execute("ALTER TABLE chat_sessions ADD COLUMN ai_transferred_at DATETIME")
            print("  Added ai_transferred_at column")

        if "ai_resolution_status" not in columns:
            cursor.execute("ALTER TABLE chat_sessions ADD COLUMN ai_resolution_status TEXT")
            print("  Added ai_resolution_status column")

        # Create knowledge_base_articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                category TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                url TEXT,
                related_articles TEXT DEFAULT '[]',
                is_published BOOLEAN DEFAULT 1,
                view_count INTEGER DEFAULT 0,
                helpful_count INTEGER DEFAULT 0,
                not_helpful_count INTEGER DEFAULT 0,
                created_by_id INTEGER REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  Created knowledge_base_articles table")

        # Create indexes for knowledge_base_articles
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_kb_category ON knowledge_base_articles(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_kb_is_published ON knowledge_base_articles(is_published)")

        # Create chat_qa_records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_qa_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES chat_sessions(id),
                reviewer_id INTEGER NOT NULL REFERENCES users(id),
                overall_score INTEGER NOT NULL,
                response_time_score INTEGER,
                resolution_score INTEGER,
                professionalism_score INTEGER,
                notes TEXT,
                tags TEXT DEFAULT '[]',
                reviewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  Created chat_qa_records table")

        # Create indexes for chat_qa_records
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_qa_session ON chat_qa_records(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_qa_reviewer ON chat_qa_records(reviewer_id)")

        conn.commit()
        print("Migration completed successfully!")
        return True

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def seed_knowledge_base():
    """Seed initial knowledge base articles."""
    print("\nSeeding knowledge base...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    articles = [
        {
            "title": "How to Download ReadIn AI",
            "content": "ReadIn AI is available for Windows, macOS, and Linux. Visit getreadin.us/download to download the desktop application for your operating system. Installation is straightforward - just run the installer and follow the prompts.",
            "summary": "Download ReadIn AI from getreadin.us/download for Windows, macOS, or Linux.",
            "category": "guide",
            "tags": '["download", "installation", "getting-started"]',
            "url": "https://getreadin.us/download"
        },
        {
            "title": "Subscription Plans and Pricing",
            "content": "ReadIn AI offers a 7-day free trial with all features. After the trial, you can subscribe to our Premium plan at $9.99/month or $99/year (save 17%). Premium includes unlimited AI responses, all meeting platforms, priority support, and advanced features.",
            "summary": "Free trial available. Premium: $9.99/month or $99/year for unlimited access.",
            "category": "faq",
            "tags": '["pricing", "subscription", "billing", "trial"]',
            "url": "https://getreadin.us/#pricing"
        },
        {
            "title": "Supported Video Meeting Platforms",
            "content": "ReadIn AI works with all major video meeting platforms including Zoom, Microsoft Teams, Google Meet, Webex, Discord, and more. The desktop app automatically detects which platform you're using and provides real-time assistance.",
            "summary": "Supports Zoom, Teams, Meet, Webex, Discord, and more.",
            "category": "feature",
            "tags": '["zoom", "teams", "meet", "platforms", "compatibility"]',
            "url": None
        },
        {
            "title": "How to Cancel Subscription",
            "content": "To cancel your subscription, go to Dashboard > Settings > Billing and click 'Manage Subscription'. You can cancel anytime and will continue to have access until the end of your current billing period. For refund requests, please contact our support team.",
            "summary": "Cancel anytime from Settings > Billing. Access continues until period end.",
            "category": "guide",
            "tags": '["cancel", "subscription", "billing"]',
            "url": None
        },
        {
            "title": "Privacy and Data Security",
            "content": "ReadIn AI processes your audio locally on your device - we never record or store your meeting audio. Only your generated responses and summaries are stored securely. You can delete your data anytime from Settings. We're GDPR compliant and take your privacy seriously.",
            "summary": "Audio processed locally. Data encrypted and GDPR compliant.",
            "category": "faq",
            "tags": '["privacy", "security", "gdpr", "data"]',
            "url": "https://getreadin.us/privacy"
        },
        {
            "title": "Troubleshooting: App Not Starting",
            "content": "If ReadIn AI isn't starting: 1) Make sure you have the latest version installed 2) Try running as administrator (Windows) or check permissions (Mac) 3) Check your antivirus isn't blocking the app 4) Restart your computer 5) If issues persist, reinstall the application.",
            "summary": "Update app, run as admin, check antivirus, restart computer.",
            "category": "troubleshooting",
            "tags": '["bug", "error", "startup", "installation"]',
            "url": None
        },
        {
            "title": "Troubleshooting: Audio Not Being Detected",
            "content": "If ReadIn AI isn't detecting audio: 1) Check your microphone permissions in system settings 2) Make sure the correct audio input is selected in ReadIn AI settings 3) Test your microphone in another application 4) Restart the meeting platform and ReadIn AI.",
            "summary": "Check mic permissions, select correct audio input, test mic, restart apps.",
            "category": "troubleshooting",
            "tags": '["audio", "microphone", "detection", "bug"]',
            "url": None
        },
        {
            "title": "Team and Enterprise Plans",
            "content": "For teams of 5+ users, we offer discounted Team plans with centralized billing and admin controls. Enterprise plans include custom integrations, SSO, dedicated support, and volume discounts. Contact sales@getreadin.us for pricing.",
            "summary": "Team plans for 5+ users. Enterprise includes SSO and custom integrations.",
            "category": "faq",
            "tags": '["team", "enterprise", "business", "pricing"]',
            "url": None
        },
    ]

    try:
        for article in articles:
            cursor.execute("""
                INSERT INTO knowledge_base_articles (title, content, summary, category, tags, url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (article["title"], article["content"], article["summary"],
                  article["category"], article["tags"], article["url"]))

        conn.commit()
        print(f"  Added {len(articles)} knowledge base articles")
        return True

    except sqlite3.IntegrityError:
        print("  Knowledge base already seeded")
        return True

    except Exception as e:
        print(f"Error seeding: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    if success:
        seed_knowledge_base()
    sys.exit(0 if success else 1)
