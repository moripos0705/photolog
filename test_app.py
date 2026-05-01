#test_step5
import os
import io
import uuid
import sqlite3
import json
import calendar as pycalendar
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from datetime import datetime
#from zeroinfo import ZoneInfo

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #すべてのアクセスを許可
    allow_methods=["*"],
    allow_headers=["*"],
)

# staticフォルダをブラウザからアクセス可能にする設定
app.mount("/static", StaticFiles(directory="static"), name="static")

model = genai.GenerativeModel('gemini-3-flash-preview')

# --- データベースの初期設定 ---
def init_db():
    conn = sqlite3.connect("photolog.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            image_path TEXT,
            content TEXT,
            mode TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def index():
    # 前回のデザインを継続（省略せずそのまま使えます）
    return """
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@700&display=swap');
                body { 
                    margin: 0; background-color: #e9e4d1; 
                    background-image: url("https://www.transparenttextures.com/patterns/natural-paper.png");
                    display: flex; justify-content: center; align-items: center; min-height: 100vh;
                    font-family: 'Noto Serif JP', serif;
                }
                .upload-box { 
                    background: #fffef9; padding: 40px; border-radius: 2px; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1); width: 320px; text-align: center;
                    border: 1px solid #dcd7bc;
                }
                h1 { color: #5d4037; font-size: 2rem; margin-bottom: 10px; letter-spacing: 0.2em; }
                p { color: #8b7355; font-size: 0.9rem; margin-bottom: 30px; }
                .submit-btn { 
                    width: 100%; padding: 12px; background: #5d4037; color: white; 
                    border: none; cursor: pointer; transition: 0.3s; letter-spacing: 0.1em;
                    font-family: 'Noto Serif JP', serif;
                }
                /* カレンダーへ飛ぶボタンのスタイル */
                .calendar-link {
                    display: block;
                    margin-top: 15px;
                    padding: 10px;
                    border: 1px solid #5d4037;
                    color: #5d4037;
                    text-decoration: none;
                    font-size: 0.85rem;
                    transition: 0.3s;
                }
                .calendar-link:hover {
                    background: #fdf5e6;
                }
            </style>
        </head>
        <body>
            <div class="upload-box">
                <h1>PhotoLog</h1>
                <p>― 写真に一句を添えて ―</p>
                <form action="/generate" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" accept="image/*" required><br>
                    <div style="text-align: left; margin: 20px 0; font-family: sans-serif; font-size: 0.85rem;">
                        <label><input type="radio" name="mode" value="horizontal" checked> 横書き</label>
                        <label style="margin-left: 10px;"><input type="radio" name="mode" value="vertical"> 縦書き</label>
                    </div>
                    <input type="submit" value="日記をしたためる" class="submit-btn">
                </form>
                
                <a href="/calendar" class="calendar-link">📅 カレンダーで振り返る</a>
            </div>
        </body>
    </html>
    """


@app.post("/generate", response_class=HTMLResponse)
async def generate(file: UploadFile = File(...), mode: str = Form("horizontal")):
    # 1. 画像の保存処理
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    save_path = f"static/uploads/{unique_filename}"
    
    image_data = await file.read()
    with open(save_path, "wb") as f:
        f.write(image_data)
    
    # 2. AIによる生成
    image = Image.open(io.BytesIO(image_data))
    prompt = """
    以下のルールに従って、この写真に対する日記を生成してください。
    - 状況を分析した140文字程度の日本語の日記。
    - たまに写真と関係のない「頓珍漢なこと」を1文だけ混ぜてもいいが、全出力に対して10%くらいの割合で混ぜること。
    - 最後に必ず「一句（五・七・五）」を添える。
    """
    response = model.generate_content([prompt, image])
    diary_text = response.text
    today = datetime.now().strftime("%Y.%m.%d")

    # 3. データベースへの保存
    conn = sqlite3.connect("photolog.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO diaries (date, image_path, content, mode) VALUES (?, ?, ?, ?)",
        (today, save_path, diary_text, mode)
    )
    conn.commit()
    conn.close()

    # 4. 表示用CSSの切り替え（前回のロジック）
    if mode == "vertical":
        content_style = "writing-mode: vertical-rl; height: 450px; margin-left: auto;"
        container_style = "display: flex; flex-direction: row-reverse; align-items: flex-start;"
        date_style = "writing-mode: vertical-rl; border-left: 2px solid #333; height: fit-content;"
    else:
        content_style = "writing-mode: horizontal-tb;"
        container_style = "display: block;"
        date_style = "border-bottom: 2px solid #333; margin-bottom: 20px;"

    return f"""
    <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&display=swap');
                body {{ font-family: 'Noto Serif JP', serif; background-color: #e9e4d1; display: flex; justify-content: center; padding: 20px; }}
                .diary-container {{ background: #fffef9; max-width: 600px; width: 100%; padding: 40px 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #dcd7bc; }}
                .photo img {{ width: 100%; border: 8px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="diary-container">
                <div style="{container_style}">
                    <div style="{date_style} font-size: 1.2rem;">{today}</div>
                    <div style="{content_style} line-height: 2.4; font-size: 1.1rem; white-space: pre-wrap;">{diary_text}</div>
                </div>
                <div class="photo"><img src="/{save_path}"></div>
                <div style="margin-top: 30px; text-align: right;">
                    <p style="font-size: 0.7rem; color: #8b7355;">※日記は保存されました</p>
                    <a href="/" style="text-decoration: none; color: #8b4513; border: 1px solid #8b4513; padding: 5px 15px; border-radius: 20px; font-size: 0.8rem;">TOPへ</a>
                </div>
            </div>
        </body>
    </html>
    """

# --- アプリ用API：日記生成 ---
# HTMLではなくJSONデータを返すバージョン
@app.post("/api/generate")
async def api_generate(file: UploadFile = File(...), mode: str = Form("horizontal")):
    # 既存の保存・生成ロジックを流用（共通化するのが理想ですが、まずは分かりやすく）
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    save_path = f"static/uploads/{unique_filename}"
    
    image_data = await file.read()
    with open(save_path, "wb") as f:
        f.write(image_data)
    
    image = Image.open(io.BytesIO(image_data))
    prompt = "写真の状況を分析した140文字程度の日記。たまに関係ない「頓珍漢なこと」を10%程度の確率で1文混ぜ、最後に五七五の一句を添えて。"
    response = model.generate_content([prompt, image])
    diary_text = response.text
    #jst = timezone(timedelta(hours=+9), 'JST')
    today = datetime.now().strftime("%Y.%m.%d")

    # DB保存
    conn = sqlite3.connect("photolog.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO diaries (date, image_path, content, mode) VALUES (?, ?, ?, ?)",
        (today, save_path, diary_text, mode)
    )
    diary_id = cursor.lastrowid # 新しく作られたIDを取得
    conn.commit()
    conn.close()

    # アプリにはHTMLではなく「データ」を返す
    return {
        "id": diary_id,
        "date": today,
        "content": diary_text,
        "image_path": f"/{save_path}",
        "mode": mode
    }

# --- 一覧ページ (History) ---
@app.get("/history", response_class=HTMLResponse)
async def history():
    conn = sqlite3.connect("photolog.db")
    conn.row_factory = sqlite3.Row  # 列名でデータを取り出せるようにする
    cursor = conn.cursor()
    # 新しい順に取得
    cursor.execute("SELECT * FROM diaries ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    #辞書のリストに変換してデータとして返す
    return [dict(row) for row in rows]

    # カード形式で並べるHTML
    cards_html = ""
    for row in rows:
        # 本文が長い場合は少しだけ表示
        summary = row["content"][:40] + "..." if len(row["content"]) > 40 else row["content"]
        cards_html += f"""
        <a href="/diary/{row['id']}" style="text-decoration: none; color: inherit;">
            <div style="background: white; border-radius: 10px; overflow: hidden; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; align-items: center; border: 1px solid #dcd7bc;">
                <img src="/{row['image_path']}" style="width: 80px; height: 80px; object-fit: cover;">
                <div style="padding: 15px;">
                    <div style="font-size: 0.8rem; color: #888;">{row['date']}</div>
                    <div style="font-size: 0.9rem; color: #5d4037; font-weight: bold;">{summary}</div>
                </div>
            </div>
        </a>
        """

    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@700&display=swap');
                body {{ background-color: #e9e4d1; font-family: 'Noto Serif JP', serif; padding: 20px; display: flex; justify-content: center; }}
                .container {{ max-width: 500px; width: 100%; }}
                h2 {{ color: #5d4037; text-align: center; letter-spacing: 0.1em; }}
                .nav-link {{ display: block; text-align: center; margin-bottom: 30px; color: #8b4513; text-decoration: none; font-size: 0.9rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>過去の綴り</h2>
                <a href="/" class="nav-link">← 新しく日記を書く</a>
                {cards_html if cards_html else "<p style='text-align:center;'>まだ日記がありません</p>"}
            </div>
        </body>
    </html>
    """

# --- アプリ用API：日記一覧取得 ---
@app.get("/api/history")
async def api_history():
    conn = sqlite3.connect("photolog.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diaries ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    data = [dict(row) for row in rows]
    return data


# --- 個別詳細ページ (Detail) ---
@app.get("/diary/{diary_id}", response_class=HTMLResponse)
async def diary_detail(diary_id: int):
    conn = sqlite3.connect("photolog.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diaries WHERE id = ?", (diary_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return HTMLResponse(content="日記が見つかりません", status_code=404)

    # データの取り出し
    mode = row["mode"]
    date = row["date"]
    content = row["content"]
    image_path = row["image_path"]

    # 表示スタイル
    if mode == "vertical":
        content_style = "writing-mode: vertical-rl; height: 450px; margin-left: auto;"
        container_style = "display: flex; flex-direction: row-reverse; align-items: flex-start;"
        date_style = "writing-mode: vertical-rl; border-left: 2px solid #333; height: fit-content;"
    else:
        content_style = "writing-mode: horizontal-tb;"
        container_style = "display: block;"
        date_style = "border-bottom: 2px solid #333; margin-bottom: 20px;"

    # HTMLを組み立てる (f-string内での変数の埋め込み)
    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&display=swap');
                body {{ font-family: 'Noto Serif JP', serif; background-color: #e9e4d1; display: flex; justify-content: center; padding: 20px; }}
                .diary-container {{ background: #fffef9; max-width: 600px; width: 100%; padding: 40px 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #dcd7bc; }}
                .photo img {{ width: 100%; border: 8px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="diary-container">
                <div style="{container_style}">
                    <div style="{date_style} font-size: 1.2rem;">{date}</div>
                    <div style="{content_style} line-height: 2.4; font-size: 1.1rem; white-space: pre-wrap;">{content}</div>
                </div>
                <div class="photo"><img src="/{image_path}"></div>
                <div style="margin-top: 30px; text-align: center;">
                    <a href="/calendar" style="text-decoration: none; color: #8b4513; font-size: 0.8rem; border-bottom: 1px solid #8b4513;">← カレンダーに戻る</a>
                </div>
            </div>
        </body>
    </html>
    """


# --- カレンダー表示 (Calendar View) ---
@app.get("/calendar", response_class=HTMLResponse)
async def calendar_view(year: int = None, month: int = None):
    now = datetime.now()
    y = year if year else now.year
    m = month if month else now.month

    # 1. データベースからその月の日記がある日を取得
    conn = sqlite3.connect("photolog.db")
    cursor = conn.cursor()
    # 日付形式 "2026.04.30" の前方一致で検索
    search_date = f"{y}.{m:02d}%"
    cursor.execute("SELECT id, date FROM diaries WHERE date LIKE ?", (search_date,))
    diaries = {row[1].split('.')[-1].lstrip('0'): row[0] for row in cursor.fetchall()}
    conn.close()

    # 2. カレンダーの作成
    cal = pycalendar.Calendar(firstweekday=6) # 日曜始まり
    month_days = cal.monthdayscalendar(y, m)

    # 前月・次月の計算
    prev_m = m - 1 if m > 1 else 12
    prev_y = y if m > 1 else y - 1
    next_m = m + 1 if m < 12 else 1
    next_y = y if m < 12 else y + 1

    # カレンダーのHTML構築
    rows_html = ""
    for week in month_days:
        rows_html += "<tr>"
        for day in week:
            if day == 0:
                rows_html += "<td></td>"
            else:
                d_str = str(day)
                if d_str in diaries:
                    # 日記がある日はリンクにする
                    rows_html += f'<td><a href="/diary/{diaries[d_str]}" class="has-diary">{day}</a></td>'
                else:
                    rows_html += f"<td>{day}</td>"
        rows_html += "</tr>"

    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@700&display=swap');
                body {{ background-color: #e9e4d1; font-family: sans-serif; padding: 20px; display: flex; justify-content: center; }}
                .calendar-container {{ background: #fffef9; padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }}
                .nav {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; font-family: 'Noto Serif JP', serif; }}
                table {{ width: 100%; border-collapse: collapse; text-align: center; }}
                th {{ padding: 10px; color: #8b7355; font-size: 0.8rem; }}
                td {{ padding: 15px 5px; font-size: 1rem; position: relative; }}
                .has-diary {{ 
                    display: inline-block; width: 30px; height: 30px; line-height: 30px; 
                    background: #5d4037; color: white !important; border-radius: 50%; text-decoration: none; 
                }}
                .back-link {{ display: block; text-align: center; margin-top: 20px; color: #8b4513; text-decoration: none; font-size: 0.8rem; }}
                h2 {{ margin: 0; color: #5d4037; }}
            </style>
        </head>
        <body>
            <div class="calendar-container">
                <div class="nav">
                    <a href="/calendar?year={prev_y}&month={prev_m}" style="text-decoration:none; color:#8b4513;">◀</a>
                    <h2>{y}年 {m}月</h2>
                    <a href="/calendar?year={next_y}&month={next_m}" style="text-decoration:none; color:#8b4513;">▶</a>
                </div>
                <table>
                    <tr><th>日</th><th>月</th><th>火</th><th>水</th><th>木</th><th>金</th><th>土</th></tr>
                    {rows_html}
                </table>
                <a href="/" class="back-link">TOPへ戻る</a>
            </div>
        </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0",port=8000)
    #uvicorn main:app --host 0.0.0.0 --port 8000 --reload
