import sys
import os

marytreat_path = os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.abspath(__file__))))

sys.path.append(marytreat_path)
sys.path.append(os.path.join(marytreat_path, "marytreat"))
sys.path.append(os.path.join(marytreat_path, "marytreat", "core"))
sys.path.append(os.path.join(marytreat_path, "marytreat", "scripts"))
sys.path.append(os.path.join(marytreat_path, "marytreat", "ui"))
