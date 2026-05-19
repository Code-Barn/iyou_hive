# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
from google.genai import Client

def list_my_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    # NO version specified here
    client = Client(api_key=api_key)

    print(f"{'MODEL NAME':<40} | {'METHODS'}")
    print("-" * 70)

    try:
        # In the new SDK, it is model.supported_methods
        for model in client.models.list():
            methods = ", ".join(model.supported_methods)
            print(f"{model.name:<40} | {methods}")
    except Exception as e:
        print(f"Failed to list models: {e}")

if __name__ == "__main__":
    list_my_models()
