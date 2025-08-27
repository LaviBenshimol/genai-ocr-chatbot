"""
chat-health-kb: preprocess HTML into structured snippets and retrieve
deterministically by (category/service/hmo/tier). Logs context sizes.
"""
from __future__ import annotations
import os
from typing import Dict, Any, List, Tuple
from bs4 import BeautifulSoup


class ChatHealthKB:
    def __init__(self, kb_dir: str):
        self.kb_dir = kb_dir
        self.by_category: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {}
        self.contacts_by_category: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._load()

    def _norm(self, t: str) -> str:
        return (t or "").strip()

    def _load(self) -> None:
        if not os.path.isdir(self.kb_dir):
            return
        for fname in os.listdir(self.kb_dir):
            if not fname.lower().endswith(".html"):
                continue
            path = os.path.join(self.kb_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")
                h2 = soup.find("h2")
                category = self._norm(h2.get_text()) if h2 else fname

                # Parse description before first table (optional)
                description_parts: List[str] = []
                for elem in soup.find_all(["p", "table"], recursive=False):
                    if elem.name == "table":
                        break
                    if elem.name == "p":
                        description_parts.append(self._norm(elem.get_text()))
                description = "\n".join([p for p in description_parts if p])

                table = soup.find("table")
                if not table:
                    # Store only description/contacts if no table
                    self.by_category.setdefault(category, {})
                    self.contacts_by_category.setdefault(category, {})
                    continue

                header_cells = table.find("tr").find_all(["th", "td"])
                funds: List[str] = []
                for cell in header_cells[1:]:
                    funds.append(self._norm(cell.get_text()))

                rows = table.find_all("tr")[1:]
                for row in rows:
                    cols = row.find_all(["th", "td"])
                    if not cols:
                        continue
                    service = self._norm(cols[0].get_text())
                    for fidx, cell in enumerate(cols[1:]):
                        fund = funds[fidx] if fidx < len(funds) else f"fund_{fidx}"
                        plans = cell.find_all("strong")
                        for plan_tag in plans:
                            plan = self._norm(plan_tag.get_text()).rstrip(":")
                            # Collect text after this <strong> until next <strong>
                            frags: List[str] = []
                            nxt = plan_tag.next_sibling
                            while nxt and not (getattr(nxt, "name", None) == "strong"):
                                txt = nxt.get_text() if hasattr(nxt, "get_text") else (nxt or "")
                                frags.append(str(txt))
                                nxt = getattr(nxt, "next_sibling", None)
                            details = self._norm("".join(frags)).lstrip(',').strip()
                            self.by_category.setdefault(category, {}) \
                                .setdefault(fund, {}) \
                                .setdefault(service, []) \
                                .append({"plan": plan, "details": details, "source_file": fname})

                # Contacts sections (optional)
                contacts = {}
                h3_app = soup.find(lambda t: t.name == "h3" and "מספרי" in t.get_text())
                if h3_app:
                    ul = h3_app.find_next("ul")
                    if ul:
                        for li in ul.find_all("li", recursive=False):
                            text = self._norm(li.get_text())
                            if ':' in text:
                                fund, rest = text.split(':', 1)
                                contacts.setdefault(fund.strip(), {})['appointment'] = rest.strip()
                h3_info = soup.find(lambda t: t.name == "h3" and "לפרטים" in t.get_text())
                if h3_info:
                    ul = h3_info.find_next("ul")
                    if ul:
                        for li in ul.find_all("li", recursive=False):
                            head = li.find(string=True, recursive=False)
                            if head:
                                fund = self._norm(head).rstrip(':')
                                phone_tag = li.find(string=lambda s: isinstance(s, str) and "טלפון:" in s)
                                if phone_tag:
                                    phone_text = str(phone_tag)
                                    phone = phone_text.split("טלפון:", 1)[-1].strip()
                                    contacts.setdefault(fund, {})['phone'] = phone
                                link = li.find("a")
                                if link and link.get('href'):
                                    contacts.setdefault(fund, {})['url'] = link['href']
                if contacts:
                    contacts.setdefault('metadata', {})['category'] = category
                    contacts['metadata']['description'] = description
                    self.contacts_by_category[category] = contacts
            except Exception:
                # skip broken files
                continue

    def retrieve(self, message: str, profile: Dict[str, Any], language: str, max_chars: int = 3500) -> Dict[str, Any]:
        """Select relevant snippets; prioritize fund/plan if present; cap total size.
        Returns snippets, citations, and size metrics.
        """
        # naive category detection: prefer dental/optometry/alternative/pregnancy/communication/workshops by keyword
        msg = (message or "").lower()
        prefer: List[str] = []
        if any(k in msg for k in ["שן", "שיניים", "dent", "oral"]):
            prefer.append("מרפאות שיניים")
        if any(k in msg for k in ["אופט", "משקפ", "optom", "vision"]):
            prefer.append("אופטומטריה")
        if any(k in msg for k in ["רפואה משלימה", "דיקור", "acupuncture", "alternative"]):
            prefer.append("רפואה משלימה")

        hmo = profile.get("hmo", "")
        tier = profile.get("tier", "")

        snippets: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []
        total_chars = 0

        cats = prefer or list(self.by_category.keys())
        for cat in cats:
            funds = self.by_category.get(cat, {})
            # If HMO provided, prioritize that fund
            fund_keys = [hmo] if hmo in funds else list(funds.keys())
            for fund in fund_keys:
                services = funds.get(fund, {})
                for svc, plans in services.items():
                    for entry in plans:
                        if tier and entry.get("plan") != tier:
                            continue
                        text = entry.get("details", "")
                        chunk = {
                            "category": cat,
                            "service": svc,
                            "fund": fund,
                            "plan": entry.get("plan"),
                            "text": text,
                            "source_file": entry.get("source_file", "")
                        }
                        add_len = len(text)
                        if total_chars + add_len > max_chars:
                            continue
                        snippets.append(chunk)
                        citations.append({
                            "source_file": entry.get("source_file", ""),
                            "category": cat,
                            "service": svc,
                            "fund": fund,
                            "plan": entry.get("plan")
                        })
                        total_chars += add_len
                        if total_chars >= max_chars:
                            break
                    if total_chars >= max_chars:
                        break
                if total_chars >= max_chars:
                    break
            if total_chars >= max_chars:
                break

        return {
            "snippets": snippets,
            "citations": citations,
            "context_chars": sum(len(s.get("text", "")) for s in snippets),
            "snippets_chars": sum(len(s.get("text", "")) for s in snippets),
        }


