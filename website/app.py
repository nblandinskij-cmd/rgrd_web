import os, json, re
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, jsonify, session

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.json')

def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "masters": [], "incomes": [], "users": {},
            "branches": ["Основной"], "pending": [],
            "payments": [], "settings": {"deduction_percent": 70},
            "admins": []
        }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ПРАЙС-ЛИСТ (такой же, как в боте)
PRICES = {
    "Мойка кузова": {
        "2-фазная мойка": [900, 1100, 1200],
        "3-фазная мойка": [1100, 1300, 1400],
        "Детейлинг кузова": [2000, 2500, 3000],
        "Твердый воск": [2000, 2500, 3000],
        "Чернение резины": 200,
        "Химчистка дисков": "200/колесо",
        "Чистка радиатора": 1500,
        "Химчистка подкапотного": 3000,
        "Консервация наружного пластика": 400,
        "Чистка хромированных элементов": "200/деталь",
        "Удаление клея, насекомых, битума": "200/деталь"
    },
    "Уборка салона": {
        "Пылесос ковра": [300, 350, 400],
        "Влажная уборка пластика": [300, 350, 400],
        "Очистка стекол": [300, 350, 400],
        "Уборка багажника": [150, 200, 250],
        "Комплексная уборка салона": [800, 900, 1000]
    },
    "Химчистка и уход": {
        "Уход за кожей": {"base": 2800, "extra_row": 1000},
        "Чистка руля": 500,
        "Увлажнение кожи": 1000,
        "Сухой туман": 600
    },
    "Дополнительно": {
        "Антидождь (полусфера/сфера)": "2000 / 3800",
        "Полировка фар (передние/в круг)": "1500 / 2800"
    },
    "Комплексные пакеты": {
        "Детейлинг-мойка": [4500, 5000, 5500]
    }
}

# Вспомогательные функции для статистики (аналогичны ботовским)
def get_branch_stats(data, branch):
    filtered = [inc for inc in data["incomes"] if inc.get("branch") == branch]
    total = sum(inc["amount"] for inc in filtered)
    count = len(filtered)
    avg = total / count if count else 0
    masters_sum = {}
    for inc in filtered:
        m = inc.get("master", "Неизвестно")
        masters_sum[m] = masters_sum.get(m, 0) + inc["amount"]
    top = sorted(masters_sum.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "total": round(total, 2),
        "count": count,
        "avg": round(avg, 2),
        "top": [{"name": m, "amount": round(s, 2)} for m, s in top]
    }

def extract_numbers(text):
    nums = []
    for word in re.findall(r'\S+', text):
        if ':' in word:
            continue
        nums.extend([float(x) for x in re.findall(r'\d+(?:\.\d+)?', word)])
    return nums

# ---------- РОУТЫ ----------
@app.route('/')
def index():
    return render_template('index.html', prices=PRICES, categories=PRICES.keys())

@app.route('/stats')
def stats():
    data = load_data()
    branches = data.get("branches", [])
    all_stats = {}
    total_all = 0
    for branch in branches:
        stats = get_branch_stats(data, branch)
        all_stats[branch] = stats
        total_all += stats["total"]
    all_masters = {}
    for inc in data["incomes"]:
        m = inc.get("master", "Неизвестно")
        all_masters[m] = all_masters.get(m, 0) + inc["amount"]
    top_masters = sorted(all_masters.items(), key=lambda x: x[1], reverse=True)[:10]
    return render_template('stats.html',
                           branches=branches,
                           all_stats=all_stats,
                           total_all=total_all,
                           top_masters=top_masters,
                           incomes=data["incomes"][-20:])

@app.route('/pending')
def pending():
    data = load_data()
    pending_list = [p for p in data.get("pending", []) if p.get("status") == "pending"]
    history = [p for p in data.get("pending", []) if p.get("status") != "pending"]
    return render_template('pending.html', pending=pending_list, history=history)

@app.route('/approve/<int:idx>')
def approve_pending(idx):
    data = load_data()
    pending_list = data.get("pending", [])
    if idx < len(pending_list) and pending_list[idx].get("status") == "pending":
        pending_list[idx]["status"] = "approved"
        inc = {
            "master": pending_list[idx]["master"],
            "branch": pending_list[idx].get("branch", "Основной"),
            "amount": pending_list[idx]["amount"],
            "date": datetime.now().isoformat(),
            "text": pending_list[idx]["text"]
        }
        data["incomes"].append(inc)
        save_data(data)
    return redirect(url_for('pending'))

@app.route('/reject/<int:idx>')
def reject_pending(idx):
    data = load_data()
    pending_list = data.get("pending", [])
    if idx < len(pending_list) and pending_list[idx].get("status") == "pending":
        pending_list[idx]["status"] = "rejected"
        save_data(data)
    return redirect(url_for('pending'))

# ---------- WEBAPP ----------
@app.route('/webapp')
def webapp():
    user_id = request.args.get('user_id')
    if not user_id:
        user_id = session.get('user_id')
        if not user_id:
            return "Ошибка: не передан user_id", 400
    user_id = int(user_id)
    session['user_id'] = user_id

    data = load_data()
    master_name = data["users"].get(str(user_id))
    admin = user_id in data.get("admins", [])

    if master_name:
        incomes = [inc for inc in data["incomes"] if inc.get("master") == master_name]
        total_income = sum(inc["amount"] for inc in incomes)
        balance = total_income - sum(pay["amount"] for pay in data["payments"] if pay.get("master") == master_name)
        recent = sorted(incomes, key=lambda x: x["date"], reverse=True)[:10]
        return render_template('webapp.html',
                               user_id=user_id,
                               master_name=master_name,
                               is_admin=admin,
                               total_income=total_income,
                               balance=balance,
                               recent_incomes=recent)
    elif admin:
        pending_list = [p for p in data.get("pending", []) if p.get("status") == "pending"]
        return render_template('webapp_admin.html', user_id=user_id, is_admin=True, pending=pending_list)
    else:
        return render_template('webapp_guest.html', user_id=user_id)

@app.route('/webapp/submit_income', methods=['POST'])
def submit_income():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"ok": False, "error": "Не авторизован"}), 401
    text = request.form.get('text', '').strip()
    if not text:
        return jsonify({"ok": False, "error": "Введите текст"}), 400
    data = load_data()
    master_name = data["users"].get(str(user_id))
    if not master_name:
        return jsonify({"ok": False, "error": "Мастер не найден"}), 404
    numbers = extract_numbers(text)
    if not numbers:
        return jsonify({"ok": False, "error": "Не найдено чисел"}), 400
    total = sum(numbers)
    percent = data["settings"].get("deduction_percent", 70)
    net = total * (100 - percent) / 100
    pending = {
        "master": master_name,
        "original_amount": total,
        "amount": net,
        "text": text,
        "date": datetime.now().isoformat(),
        "status": "pending"
    }
    data["pending"].append(pending)
    save_data(data)
    return jsonify({"ok": True, "amount": net, "message": "Заявка отправлена"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)