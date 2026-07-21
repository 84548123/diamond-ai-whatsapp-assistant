import pandas as pd
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..db.models import StockItem
from ..core.config import settings
from ..db.chroma_client import get_stock_collection
import json

class StockService:
    def __init__(self):
        self.csv_path = settings.STOCK_CSV_PATH
        self.df = None
        self._load_stock_data()

    def _load_stock_data(self):
        """Load stock CSV into memory and sync to DB / Chroma if needed."""
        if not os.path.exists(self.csv_path):
            print(f"WARNING: Stock CSV not found at {self.csv_path}")
            self.df = pd.DataFrame()
            return

        self.df = pd.read_csv(self.csv_path)
        self.df.columns = [c.strip().replace(" ", "_").lower() for c in self.df.columns]

        # Rename for consistency
        col_map = {
            "srno": "srno",
            "loc": "loc",
            "rep_no": "rep_no",
            "stone_no": "stone_no",
            "shp": "shp",
            "cts": "cts",
            "col": "col",
            "clr": "clr",
            "cut": "cut",
            "pol": "pol",
            "sym": "sym",
            "lab": "lab",
            "fluro": "fluro",
            "length": "length",
            "width": "width",
            "height": "height",
            "l:w": "lw",
            "tbl": "tbl",
            "td%": "td",
            "girdle": "girdle",
            "bic": "bic",
            "bis": "bis",
            "tinge": "tinge",
            "comments": "comments",
            "video_link": "video_link",
            "image_link": "image_link",
            "certificate_link": "certificate_link"
        }
        self.df = self.df.rename(columns={k: v for k, v in col_map.items() if k in self.df.columns})

        # Ensure required columns
        required = ["rep_no", "stone_no", "shp", "cts", "col", "clr", "lab"]
        for col in required:
            if col not in self.df.columns:
                self.df[col] = ""

        self.df["is_available"] = True
        print(f"✅ Loaded {len(self.df)} stock items from CSV")

    def get_stock_by_rep_no(self, rep_no: str) -> Optional[Dict]:
        if self.df is None or self.df.empty:
            return None
        match = self.df[self.df["rep_no"].astype(str) == str(rep_no)]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    def get_stock_by_stone_no(self, stone_no: str) -> Optional[Dict]:
        if self.df is None or self.df.empty:
            return None
        match = self.df[self.df["stone_no"].astype(str).str.upper() == str(stone_no).upper()]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    def search_stock(self, query: str = "", rep_no: str = None, stone_no: str = None, limit: int = 8) -> List[Dict]:
        """Smart search: by rep_no, stone_no, or free text."""
        if self.df is None or self.df.empty:
            return []

        df = self.df.copy()

        if rep_no:
            df = df[df["rep_no"].astype(str) == str(rep_no)]
        if stone_no:
            df = df[df["stone_no"].astype(str).str.upper().str.contains(str(stone_no).upper(), na=False)]

        if query and not (rep_no or stone_no):
            q = query.lower().strip()
            # Free-text search on key columns
            mask = (
                df["rep_no"].astype(str).str.contains(q, case=False, na=False) |
                df["stone_no"].astype(str).str.contains(q, case=False, na=False) |
                df["shp"].astype(str).str.contains(q, case=False, na=False) |
                df["col"].astype(str).str.contains(q, case=False, na=False) |
                df["clr"].astype(str).str.contains(q, case=False, na=False) |
                df["comments"].astype(str).str.contains(q, case=False, na=False)
            )
            df = df[mask]

        results = df.head(limit).to_dict(orient="records")
        return results

    def format_stock_response(self, items: List[Dict]) -> str:
        """Human-readable formatted response for WhatsApp."""
        if not items:
            return "❌ Sorry, no matching diamonds found in our current stock. Would you like me to search for similar stones?"

        response_parts = ["✅ **Found in Stock:**\n"]
        for i, item in enumerate(items[:5], 1):
            rep = item.get("rep_no", "N/A")
            stone = item.get("stone_no", "N/A")
            shp = item.get("shp", "")
            cts = item.get("cts", 0)
            col = item.get("col", "")
            clr = item.get("clr", "")
            lab = item.get("lab", "")
            loc = item.get("loc", "MUMBAI")

            msg = (
                f"**{i}. Rep No: {rep}**\n"
                f"   Stone/Packet: {stone}\n"
                f"   Shape: {shp} | {cts}ct | {col} | {clr}\n"
                f"   Lab: {lab} | Location: {loc}\n"
                f"   ✅ **IN STOCK**\n"
            )

            # Add links if present
            links = []
            if item.get("video_link") and item["video_link"] != "Video":
                links.append(f"[Video]({item['video_link']})")
            if item.get("image_link") and item["image_link"] != "Image":
                links.append(f"[Image]({item['image_link']})")
            if item.get("certificate_link") and item["certificate_link"] != "Certificate":
                links.append(f"[Cert]({item['certificate_link']})")

            if links:
                msg += "   " + " | ".join(links) + "\n"

            response_parts.append(msg)

        if len(items) > 5:
            response_parts.append(f"\n... and {len(items) - 5} more. Say 'show all' or specify a Rep No.")

        response_parts.append("\n📍 Would you like details, a quote, or to book a viewing?")
        return "\n".join(response_parts)

    def sync_to_postgres(self, db: Session):
        """One-time or periodic sync of CSV to Postgres (for production)"""
        if self.df is None or self.df.empty:
            return

        count = 0
        for _, row in self.df.iterrows():
            existing = db.query(StockItem).filter(StockItem.rep_no == str(row.get("rep_no"))).first()
            if not existing:
                item = StockItem(
                    srno=int(row.get("srno", 0)),
                    loc=str(row.get("loc", "")),
                    rep_no=str(row.get("rep_no", "")),
                    stone_no=str(row.get("stone_no", "")),
                    shp=str(row.get("shp", "")),
                    cts=float(row.get("cts", 0)),
                    col=str(row.get("col", "")),
                    clr=str(row.get("clr", "")),
                    cut=str(row.get("cut", "")),
                    pol=str(row.get("pol", "")),
                    sym=str(row.get("sym", "")),
                    lab=str(row.get("lab", "")),
                    fluro=str(row.get("fluro", "")),
                    length=float(row.get("length", 0) or 0),
                    width=float(row.get("width", 0) or 0),
                    height=float(row.get("height", 0) or 0),
                    lw=float(row.get("lw", 0) or 0),
                    tbl=float(row.get("tbl", 0) or 0),
                    td=float(row.get("td", 0) or 0),
                    girdle=str(row.get("girdle", "")),
                    bic=str(row.get("bic", "")),
                    bis=str(row.get("bis", "")),
                    tinge=str(row.get("tinge", "")),
                    comments=str(row.get("comments", ""))[:500],
                    video_link=str(row.get("video_link", "")),
                    image_link=str(row.get("image_link", "")),
                    certificate_link=str(row.get("certificate_link", "")),
                    is_available=True,
                )
                db.add(item)
                count += 1
        db.commit()
        print(f"✅ Synced {count} new stock items to PostgreSQL")

    def get_all_rep_nos(self) -> List[str]:
        if self.df is None:
            return []
        return self.df["rep_no"].astype(str).tolist()
