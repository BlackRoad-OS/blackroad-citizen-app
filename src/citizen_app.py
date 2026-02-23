"""Civic Engagement App Backend - Issue reporting and voting system."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3
import json
import os
from pathlib import Path

@dataclass
class Issue:
    """Represents a civic issue report."""
    id: str
    title: str
    category: str
    location: str
    status: str = "open"
    votes: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class CitizenAppBackend:
    """Backend for citizen engagement app with SQLite persistence."""
    
    CATEGORIES = {"infrastructure", "safety", "environment", "community", "transit"}
    DB_PATH = Path.home() / ".blackroad" / "citizen.db"
    
    def __init__(self):
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                votes INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    
    def report_issue(self, title: str, category: str, location: str) -> str:
        """Create new issue report."""
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {self.CATEGORIES}")
        
        issue_id = f"issue_{datetime.now().timestamp()}"
        issue = Issue(id=issue_id, title=title, category=category, location=location)
        
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO issues (id, title, category, location, status, votes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (issue.id, issue.title, issue.category, issue.location, 
              issue.status, issue.votes, issue.created_at))
        
        conn.commit()
        conn.close()
        
        return issue_id
    
    def vote_issue(self, issue_id: str) -> int:
        """Increment vote count for an issue."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE issues SET votes = votes + 1 WHERE id = ?", (issue_id,))
        
        cursor.execute("SELECT votes FROM issues WHERE id = ?", (issue_id,))
        result = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        return result[0] if result else 0
    
    def get_issues(self, category: Optional[str] = None, sort_by: str = "votes") -> List[Dict[str, Any]]:
        """Retrieve issues with optional filtering and sorting."""
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM issues"
        params = []
        
        if category:
            query += " WHERE category = ?"
            params.append(category)
        
        if sort_by == "votes":
            query += " ORDER BY votes DESC, created_at DESC"
        elif sort_by == "recent":
            query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics on reported issues."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM issues")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(votes) FROM issues")
        avg_votes = cursor.fetchone()[0] or 0
        
        by_category = {}
        for cat in self.CATEGORIES:
            cursor.execute("SELECT COUNT(*) FROM issues WHERE category = ?", (cat,))
            by_category[cat] = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_issues": total,
            "average_votes": round(avg_votes, 2),
            "by_category": by_category
        }
    
    def export_json(self) -> str:
        """Export all issues as JSON."""
        issues = self.get_issues(sort_by="recent")
        stats = self.get_stats()
        
        export_data = {
            "statistics": stats,
            "issues": issues
        }
        
        return json.dumps(export_data, indent=2)


def main():
    """CLI interface."""
    import sys
    
    app = CitizenAppBackend()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python citizen_app.py report \"Title\" category \"lat,lon\"")
        print("  python citizen_app.py list")
        print("  python citizen_app.py stats")
        return
    
    command = sys.argv[1]
    
    if command == "report" and len(sys.argv) >= 5:
        title = sys.argv[2]
        category = sys.argv[3]
        location = sys.argv[4]
        
        issue_id = app.report_issue(title, category, location)
        print(f"✓ Issue reported: {issue_id}")
    
    elif command == "list":
        issues = app.get_issues()
        print(f"\nFound {len(issues)} issues:\n")
        for issue in issues:
            print(f"  [{issue['category']:12s}] {issue['title'][:40]:40s} | Votes: {issue['votes']:3d}")
    
    elif command == "stats":
        stats = app.get_stats()
        print(f"\nStats:")
        print(f"  Total Issues: {stats['total_issues']}")
        print(f"  Avg Votes: {stats['average_votes']}")
        print(f"  By Category:")
        for cat, count in stats['by_category'].items():
            print(f"    {cat:15s}: {count}")


if __name__ == "__main__":
    main()
