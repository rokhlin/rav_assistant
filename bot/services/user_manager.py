import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class UserManagerService:
    def __init__(self, config_file: Optional[Path] = None):
        if config_file is not None:
            self.file_path = Path(config_file)
        else:
            config_dir = Path("data/config")
            config_dir.mkdir(parents=True, exist_ok=True)
            self.file_path = config_dir / "users.json"

        self._users: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        """Load users from file or seed from config/env."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._users = json.load(f)
                return
            except Exception as e:
                logger.warning(f"Failed to read {self.file_path}: {e}")
                self._users = {}

        # If file does not exist, seed from environment/settings
        self._seed_from_config()

    def _seed_from_config(self):
        from config import settings

        seeded: Dict[str, Dict[str, Any]] = {}
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Parse admin IDs
        admin_ids = set()
        raw_admins = getattr(settings, "ADMIN_USER_IDS", "").strip()
        if raw_admins:
            for aid in raw_admins.split(","):
                aid_clean = aid.strip()
                if aid_clean.isdigit():
                    admin_ids.add(int(aid_clean))

        # Parse ALLOWED_USERS (format: "123:Alex, 456:Maria")
        raw_users = settings.ALLOWED_USERS.strip()
        if raw_users:
            for part in raw_users.split(","):
                part_clean = part.strip()
                if not part_clean:
                    continue
                if ":" in part_clean:
                    uid_str, name = part_clean.split(":", 1)
                    uid_str, name = uid_str.strip(), name.strip()
                    if uid_str.isdigit():
                        uid_int = int(uid_str)
                        is_adm = uid_int in admin_ids or (not admin_ids and len(seeded) == 0)
                        seeded[uid_str] = {
                            "name": name or f"User {uid_str}",
                            "role": "admin" if is_adm else "user",
                            "added_at": now_str
                        }
                elif part_clean.isdigit():
                    uid_int = int(part_clean)
                    is_adm = uid_int in admin_ids or (not admin_ids and len(seeded) == 0)
                    seeded[part_clean] = {
                        "name": f"User {part_clean}",
                        "role": "admin" if is_adm else "user",
                        "added_at": now_str
                    }

        # Fallback to ALLOWED_USER_IDS
        raw_ids = settings.ALLOWED_USER_IDS.strip()
        if raw_ids:
            for uid in raw_ids.split(","):
                uid_clean = uid.strip()
                if uid_clean.isdigit() and uid_clean not in seeded:
                    uid_int = int(uid_clean)
                    is_adm = uid_int in admin_ids or (not admin_ids and len(seeded) == 0)
                    seeded[uid_clean] = {
                        "name": f"User {uid_clean}",
                        "role": "admin" if is_adm else "user",
                        "added_at": now_str
                    }

        # If admin_ids were specified but not in seeded users, add them as admins
        for aid in admin_ids:
            aid_str = str(aid)
            if aid_str not in seeded:
                seeded[aid_str] = {
                    "name": f"Admin {aid_str}",
                    "role": "admin",
                    "added_at": now_str
                }

        self._users = seeded
        if seeded:
            self._save()

    def _save(self):
        """Persist users to JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving users to {self.file_path}: {e}")

    def get_allowed_users_map(self) -> Dict[int, str]:
        """Returns mapping of {user_id: user_name} for all allowed users."""
        mapping: Dict[int, str] = {}
        for uid_str, data in self._users.items():
            if uid_str.isdigit():
                mapping[int(uid_str)] = data.get("name", f"User {uid_str}")
        return mapping

    def get_allowed_user_ids(self) -> List[int]:
        """Returns list of integer IDs of allowed users."""
        return list(self.get_allowed_users_map().keys())

    def is_allowed(self, user_id: Optional[int]) -> bool:
        """Check if user has access."""
        if not user_id:
            return False
        # If no users configured at all, system is open
        if not self._users:
            return True
        return str(user_id) in self._users

    def is_admin(self, user_id: Optional[int]) -> bool:
        """Check if user has administrator privileges."""
        if not user_id:
            return False
        user_data = self._users.get(str(user_id))
        if not user_data:
            return False
        return user_data.get("role") == "admin"

    def get_admin_ids(self) -> List[int]:
        """Get IDs of all administrators."""
        admins = []
        for uid_str, data in self._users.items():
            if data.get("role") == "admin" and uid_str.isdigit():
                admins.append(int(uid_str))
        # Fallback: if no admin marked, use the first user
        if not admins and self._users:
            first_uid = next(iter(self._users))
            if first_uid.isdigit():
                admins.append(int(first_uid))
        return admins

    def get_user_name(self, user_id: int) -> str:
        """Get user's display name."""
        user_data = self._users.get(str(user_id))
        if user_data and user_data.get("name"):
            return user_data["name"]
        return f"User {user_id}"

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user info dict."""
        return self._users.get(str(user_id))

    def get_all_users(self) -> Dict[str, Dict[str, Any]]:
        """Get copy of all users dict."""
        return dict(self._users)

    def add_user(
        self,
        user_id: int,
        name: str,
        role: str = "user",
        username: Optional[str] = None
    ) -> bool:
        """Add or update an allowed user."""
        uid_str = str(user_id)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._users[uid_str] = {
            "name": name.strip() or f"User {uid_str}",
            "role": role,
            "username": username or "",
            "added_at": now_str
        }
        self._save()
        logger.info(f"User {uid_str} ({name}) added with role '{role}'")
        return True

    def update_user_name(self, user_id: int, new_name: str) -> bool:
        """Update user display name."""
        uid_str = str(user_id)
        if uid_str in self._users:
            self._users[uid_str]["name"] = new_name.strip()
            self._save()
            logger.info(f"User {uid_str} renamed to '{new_name}'")
            return True
        return False

    def remove_user(self, user_id: int) -> bool:
        """Remove user from allowed list."""
        uid_str = str(user_id)
        if uid_str in self._users:
            del self._users[uid_str]
            self._save()
            logger.info(f"User {uid_str} removed from allowed list")
            return True
        return False

user_manager = UserManagerService()
