import csv
import os
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta

app = Flask(__name__)



STAFF_CSV = 'staff.csv'
SHIFT_CSV = 'shift.csv'

def handle_csv_upload(file_storage, fieldnames):
    rows = []
    if file_storage:
        stream = file_storage.stream.read().decode("utf-8").splitlines()
        reader = csv.DictReader(stream)
        for row in reader:
            if all(field in row for field in fieldnames):
                rows.append(row)
    return rows

def append_to_csv(csv_path, rows, fieldnames):
    file_exists = os.path.exists(csv_path)
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writeheader()
        writer.writerows(rows)

# 並び順で使うラベルマップ
group_name_map = {
    0: "社員",
    1: "複数時間帯バイト（両方対応）",
    2: "複数時間帯バイト（キッチン専属）",
    3: "複数時間帯バイト（トップ専属）",
    4: "朝バイト（両方対応）",
    5: "朝バイト（キッチン専属）",
    6: "朝バイト（トップ専属）",
    7: "昼バイト（両方対応）",
    8: "昼バイト（キッチン専属）",
    9: "昼バイト（トップ専属）",
    10: "夜バイト（両方対応）",
    11: "夜バイト（キッチン専属）",
    12: "夜バイト（トップ専属）",
    13: "その他"
}

STAFF_CSV = 'staff.csv'
SHIFT_CSV = 'shift.csv'

def load_staff():
    staff_list = []
    try:
        with open(STAFF_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                staff = {
                    'name': row['name'],
                    'position': row['position'],
                    'experience': row['experience'],
                    'role': row.get('role', '両方'),
                    'time_category': row.get('time_category', '複数')
                }
                staff_list.append(staff)
    except FileNotFoundError:
        pass
    return sort_staff_list(staff_list)

def sort_staff_list(staff_list):
    def score(staff):
        if staff['position'] == '社員':
            staff['group'] = 0
            return (0, 0, staff['name'])

        time_map = {'複数': 1, '朝': 2, '昼': 3, '夜': 4}
        time_score = time_map.get(staff.get('time_category', '複数'), 5)
        role_score = {'両方': 0, 'キッチン': 1, 'トップ': 2}.get(staff.get('role', ''), 3)
        exp_score = 0 if staff['experience'] == 'ベテラン' else 1
        group = (time_score - 1) * 3 + 1 + role_score
        staff['group'] = group
        return (group, exp_score, staff['name'])

    return sorted(staff_list, key=score)

staff_list = load_staff()
shift_list = []  # 後で load_shifts() などで再定義


def save_staff(staff):
    file_exists = os.path.exists(STAFF_CSV)
    with open(STAFF_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'position', 'experience', 'time_type'])
        if not file_exists or os.path.getsize(STAFF_CSV) == 0:
            writer.writeheader()
        writer.writerow(staff)

def load_shifts():
    shift_list = []
    try:
        with open(SHIFT_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                shift_list.append({
                    'staff_name': row['staff_name'],
                    'date': row['date'],
                    'start': row['start'],
                    'end': row['end']
                })
    except FileNotFoundError:
        pass
    return shift_list

def save_shift(shift):
    file_exists = False
    try:
        with open(SHIFT_CSV, 'r', encoding='utf-8') as f:
            file_exists = True
    except FileNotFoundError:
        pass
    with open(SHIFT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['staff_name', 'date', 'start', 'end'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(shift)

staff_list = load_staff()
shift_list = load_shifts()

def generate_date_list():
    base = datetime(2025, 5, 1)
    return [(base + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(31)]

def build_shift_dict():
    shift_dict = {staff['name']: {} for staff in staff_list}
    for shift in shift_list:
        staff_name = shift['staff_name']
        if staff_name not in shift_dict:
            continue  # ← これを追加！
        shift_dict[staff_name][shift['date']] = (shift['start'], shift['end'])
    return shift_dict

def calculate_shift_hours(start, end):
    start_time = datetime.strptime(start, '%H:%M')
    end_time = datetime.strptime(end, '%H:%M')
    return max((end_time - start_time).total_seconds() / 3600 - 1, 0)

def generate_time_slots(start='07:00', end='23:30'):
    slots = []
    current = datetime.strptime(start, '%H:%M')
    end_time = datetime.strptime(end, '%H:%M')
    while current <= end_time:
        slots.append(current.strftime('%H:%M'))
        current += timedelta(minutes=30)
    return slots

def generate_detailed_daily_counts():
    time_slots = generate_time_slots()
    day_counts = {}

    # すべての日付を初期化（人数0）
    for i in range(30):
        date = (datetime(2025, 4, 1) + timedelta(days=i)).strftime('%Y-%m-%d')
        day_counts[date] = {slot: {'total': 0, 'veteran': 0, 'employee': 0} for slot in time_slots}

    staff_info = {s['name']: s for s in staff_list}

    for shift in shift_list:
        name = shift['staff_name']
        date = shift['date']
        start = datetime.strptime(shift['start'], '%H:%M')
        end = datetime.strptime(shift['end'], '%H:%M')

        current = start
        while current < end:
            slot = current.strftime('%H:%M')
            if slot in day_counts[date]:  # 念のためチェック
                day_counts[date][slot]['total'] += 1
                if staff_info[name]['experience'] == 'ベテラン':
                    day_counts[date][slot]['veteran'] += 1
                if staff_info[name]['position'] == '社員':
                    day_counts[date][slot]['employee'] += 1
            current += timedelta(minutes=30)

    return day_counts


def generate_role_based_counts():
    time_slots = generate_time_slots()
    day_counts = {}
    staff_info = {s['name']: s for s in staff_list}

    for shift in shift_list:
        name = shift['staff_name']
        date = shift['date']
        start = datetime.strptime(shift['start'], '%H:%M')
        end = datetime.strptime(shift['end'], '%H:%M')

        if date not in day_counts:
            day_counts[date] = {slot: {
                'total': 0,
                'kitchen': 0,
                'top': 0,
                'kitchen_vet': 0,
                'top_vet': 0
            } for slot in time_slots}

        info = staff_info.get(name)
        if not info:
            continue

        role = info.get('role', '両方')
        is_veteran = info.get('experience') == 'ベテラン'

        current = start
        while current < end:
            slot = current.strftime('%H:%M')
            if slot not in day_counts[date]:
                current += timedelta(minutes=30)
                continue

            day_counts[date][slot]['total'] += 1

            if role == '両方':
                day_counts[date][slot]['kitchen'] += 0.5
                day_counts[date][slot]['top'] += 0.5
                if is_veteran:
                    day_counts[date][slot]['kitchen_vet'] += 0.5
                    day_counts[date][slot]['top_vet'] += 0.5
            elif role == 'キッチン':
                day_counts[date][slot]['kitchen'] += 1
                if is_veteran:
                    day_counts[date][slot]['kitchen_vet'] += 1
            elif role == 'トップ':
                day_counts[date][slot]['top'] += 1
                if is_veteran:
                    day_counts[date][slot]['top_vet'] += 1

            current += timedelta(minutes=30)

    return day_counts



def generate_detailed_role_counts():
    time_slots = generate_time_slots()
    day_counts = {}
    staff_info = {s['name']: s for s in staff_list}

    for shift in shift_list:
        name = shift['staff_name']
        date = shift['date']
        start = datetime.strptime(shift['start'], '%H:%M')
        end = datetime.strptime(shift['end'], '%H:%M')

        if date not in day_counts:
            day_counts[date] = {slot: {
                'total': 0,
                'kitchen_total': 0,
                'top_total': 0,
                'kitchen_veteran': 0,
                'top_veteran': 0
            } for slot in time_slots}

        current = start
        while current < end:
            slot = current.strftime('%H:%M')
            info = staff_info.get(name)
            if not info or slot not in day_counts[date]:
                current += timedelta(minutes=30)
                continue

            day_counts[date][slot]['total'] += 1

            if info['role'] == '両方':
                day_counts[date][slot]['kitchen_total'] += 0.5
                day_counts[date][slot]['top_total'] += 0.5
                if info['experience'] == 'ベテラン':
                    day_counts[date][slot]['kitchen_veteran'] += 0.5
                    day_counts[date][slot]['top_veteran'] += 0.5
            elif info['role'] == 'キッチン':
                day_counts[date][slot]['kitchen_total'] += 1
                if info['experience'] == 'ベテラン':
                    day_counts[date][slot]['kitchen_veteran'] += 1
            elif info['role'] == 'トップ':
                day_counts[date][slot]['top_total'] += 1
                if info['experience'] == 'ベテラン':
                    day_counts[date][slot]['top_veteran'] += 1

            current += timedelta(minutes=30)

    return day_counts





def generate_compact_bar_data():
    staff_info = {s['name']: s for s in staff_list}
    result = {}

    # 日付をすべて取得（例：2025-05-01〜31）
    all_dates = generate_date_list()

    for date in all_dates:
        segments = []
        slots = generate_time_slots('07:00', '23:30')  # 固定時間
        shifts_for_date = [s for s in shift_list if s['date'] == date]

        if not shifts_for_date:
            # シフトがない日はすべて0人の1本の棒で表示
            segments.append({
                "start": "07:00",
                "end": "23:30",
                "count": 0,
                "duration": (datetime.strptime("23:30", "%H:%M") - datetime.strptime("07:00", "%H:%M")).seconds / 60
            })
            # 下端合わせのダミー（23:30）
            segments.append({
                "start": "23:30",
                "end": "23:30",
                "count": 0,
                "duration": 0.1
            })
            result[date] = segments
            continue

        last_count = -1
        current_start = slots[0]

        for slot in slots:
            count = sum(
                1 for s in shifts_for_date if
                datetime.strptime(s['start'], '%H:%M') <= datetime.strptime(slot, '%H:%M') <
                datetime.strptime(s['end'], '%H:%M')
            )
            if count != last_count:
                if last_count != -1:
                    duration = (
                        datetime.strptime(slot, '%H:%M') - datetime.strptime(current_start, '%H:%M')
                    ).seconds / 60
                    segments.append({
                        "start": current_start,
                        "end": slot,
                        "count": last_count,
                        "duration": duration
                    })
                current_start = slot
                last_count = count

        # 最終セグメント
        duration = (
            datetime.strptime("23:30", "%H:%M") - datetime.strptime(current_start, "%H:%M")
        ).seconds / 60
        if duration > 0:
            segments.append({
                "start": current_start,
                "end": "23:30",
                "count": last_count,
                "duration": duration
            })

        # ダミーで23:30のラベルを揃える
        segments.append({
            "start": "23:30",
            "end": "23:30",
            "count": 0,
            "duration": 0.1
        })

        result[date] = segments
    return result


def float_to_time_string(value):
    try:
        value = float(value)
        hour = int(value)
        minute = int(round((value - hour) * 60))
        return f"{hour:02d}:{minute:02d}"
    except:
        return ""



@app.route('/graph/vertical')
def graph_vertical():
    bar_data = generate_compact_bar_data()
    return render_template('graph_vertical.html', bar_data=bar_data)


@app.route('/')
def index():
    dates = generate_date_list()
    shifts = build_shift_dict()
    total_hours = {}
    for staff in staff_list:
        if staff['position'] == '社員':
            total = 0
            for date, times in shifts[staff['name']].items():
                total += calculate_shift_hours(*times)
            total_hours[staff['name']] = total
    return render_template('index.html',
                            dates=dates,
                            staff_list=staff_list,
                            shifts=shifts,
                            total_hours=total_hours,
                            calculate_shift_hours=calculate_shift_hours,
                            group_name_map=group_name_map)

@app.route('/graph')
def graph():
    time_slots = generate_time_slots()
    day_counts = generate_detailed_daily_counts()
    return render_template('graph.html', time_slots=time_slots, day_counts=day_counts)


@app.route('/graph/<mode>')
def graph_mode(mode):
    time_slots = generate_time_slots()
    day_counts = generate_detailed_role_counts()

    return render_template('graph_mode.html', 
                           time_slots=time_slots, 
                           day_counts=day_counts, 
                           mode=mode)

# 上記ルートを app.py に追加してください（graph() の下など）


@app.route('/staff/add', methods=['GET', 'POST'])
def add_staff():
    global staff_list
    if request.method == 'POST':
        staff = {
            'name': request.form['name'],
            'position': request.form['position'],
            'experience': request.form['experience'],
            'role': request.form['role'],
            'time_category': request.form['time_category']
        }
        staff_list.append(staff)
        staff_list = sort_staff_list(staff_list)

        with open(STAFF_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'position', 'experience', 'role', 'time_category'])
            if os.path.getsize(STAFF_CSV) == 0:
                writer.writeheader()
            # 🔥 group を除いて書き込む
            writer.writerow({k: staff[k] for k in ['name', 'position', 'experience', 'role', 'time_category']})

        return redirect(url_for('index'))
    return render_template('staff_add.html')


@app.route('/shift/add', methods=['GET', 'POST'])
def add_shift():
    if request.method == 'POST':
        shift = {
            'staff_name': request.form['staff_name'],
            'date': request.form['date'],
            'start': request.form['start'],
            'end': request.form['end']
        }
        shift_list.append(shift)
        save_shift(shift)
        return redirect(url_for('index'))
    return render_template('add_shift.html', staff_list=staff_list)


@app.route('/template_assign', methods=['GET', 'POST'])
def template_assign():
    if request.method == 'POST':
        staff_name = request.form['staff_name']
        templates = {}
        for i in range(7):
            start = request.form.get(f'start_{i}')
            end = request.form.get(f'end_{i}')
            if start and end:
                templates[i] = (start, end)
        base = datetime(2025, 4, 1)
        for i in range(30):
            day = base + timedelta(days=i)
            weekday = day.weekday()
            if weekday in templates:
                start, end = templates[weekday]
                date_str = day.strftime('%Y-%m-%d')
                shift = {
                    'staff_name': staff_name,
                    'date': date_str,
                    'start': start,
                    'end': end
                }
                shift_list.append(shift)
                with open(SHIFT_CSV, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['staff_name', 'date', 'start', 'end'])
                    if f.tell() == 0:
                        writer.writeheader()
                    writer.writerow(shift)
        return redirect(url_for('index'))
    return render_template('template_assign.html', staff_list=staff_list)

def register_upload_routes(app, staff_list, shift_list, staff_csv='staff.csv', shift_csv='shift.csv'):
    @app.route('/staff/upload', methods=['GET', 'POST'])
    def upload_staff():
        global staff_list
        STAFF_FIELDS = ['name', 'position', 'experience', 'role', 'time_category']  # 安全のため定義

        if request.method == 'POST':
            file = request.files.get('file')
            if file:
                stream = file.stream.read().decode("utf-8").splitlines()
                reader = csv.DictReader(stream)
                new_staff = []
                for row in reader:
                    staff = {
                        'name': row['name'],
                        'position': row['position'],
                        'experience': row['experience'],
                        'role': row.get('role', '両方'),
                        'time_category': row.get('time_category', '複数')
                    }
                    new_staff.append(staff)
                    staff_list.append(staff)

                staff_list = sort_staff_list(staff_list)

                with open(STAFF_CSV, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=STAFF_FIELDS)
                    if os.path.getsize(STAFF_CSV) == 0:
                        writer.writeheader()
                    for staff in new_staff:
                        writer.writerow({key: staff[key] for key in STAFF_FIELDS})  # groupを除外

            return redirect(url_for('index'))
        return render_template('staff_upload.html')

    @app.route('/shift/upload', methods=['GET', 'POST'])
    def upload_shift():
        if request.method == 'POST':
            file = request.files.get('file')
            rows = handle_csv_upload(file, ['staff_name', 'date', 'start', 'end'])

            fixed_rows = []
            for row in rows:
                day = row['date'].zfill(2)
                full_date = f"2025-05-{day}"
                shift = {
                    'staff_name': row['staff_name'],
                    'date': full_date,
                    'start': float_to_time_string(row.get('start', '')),
                    'end': float_to_time_string(row.get('end', ''))
                }
                fixed_rows.append(shift)

            shift_list.extend(fixed_rows)
            append_to_csv(SHIFT_CSV, fixed_rows, ['staff_name', 'date', 'start', 'end'])
            return redirect(url_for('index'))
        return render_template('shift_upload.html')

@app.route('/shift/save', methods=['POST'])
def save_edited_shifts():
    global shift_list
    shift_list = []
    for staff in staff_list:
        for date in generate_date_list():
            start_key = f"start_{staff['name']}_{date}"
            end_key = f"end_{staff['name']}_{date}"
            start = request.form.get(start_key)
            end = request.form.get(end_key)
            if not start or not end:
                continue
            shift = {
                'staff_name': staff['name'],
                'date': date,
                'start': start,
                'end': end
            }
            shift_list.append(shift)
    with open(SHIFT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['staff_name', 'date', 'start', 'end'])
        writer.writeheader()
        writer.writerows(shift_list)
    return redirect(url_for('index'))


@app.route('/staff/edit', methods=['GET', 'POST'])
def edit_staff():
    global staff_list

    if request.method == 'POST':
        original_names = request.form.getlist('original_name')
        updated_staff_list = []

        for i, original_name in enumerate(original_names):
            name = request.form.get(f'name_{i}')
            position = request.form.get(f'position_{i}')
            experience = request.form.get(f'experience_{i}')
            role = request.form.get(f'role_{i}')
            time_category = request.form.get(f'time_category_{i}')

            updated_staff_list.append({
                'name': name,
                'position': position,
                'experience': experience,
                'role': role,
                'time_category': time_category
            })

        staff_list = sort_staff_list(updated_staff_list)

        # CSVに保存（groupは除く）
        with open(STAFF_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'position', 'experience', 'role', 'time_category'])
            writer.writeheader()
            for staff in staff_list:
                writer.writerow({key: staff[key] for key in writer.fieldnames})

        # shift.csv の名前も更新
        if os.path.exists(SHIFT_CSV):
            updated_shifts = []
            with open(SHIFT_CSV, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for i, original_name in enumerate(original_names):
                        if row['staff_name'] == original_name:
                            row['staff_name'] = updated_staff_list[i]['name']
                            break
                    updated_shifts.append(row)
            with open(SHIFT_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['staff_name', 'date', 'start', 'end'])
                writer.writeheader()
                writer.writerows(updated_shifts)

        return redirect(url_for('index'))

    return render_template('staff_edit.html', staff_list=staff_list)


@app.route("/submit_shift/<name>", methods=["GET", "POST"])
def submit_shift(name):
    if request.method == "POST":
        shifts = {}
        for key in request.form:
            if key.startswith("start_"):
                date = key.split("_", 1)[1]
                start = request.form.get(f"start_{date}")
                end = request.form.get(f"end_{date}")
                wished = request.form.get(f"wished_{date}")
                if start and end and wished:
                    shifts[date] = {
                        "start": start,
                        "end": end,
                        "wished": float(wished)
                    }
        # 保存処理（例：CSVやJSON）
        print(shifts)  # デバッグ表示
        return "シフトを保存しました！"

    return render_template("submit_shift.html", name=name)




if __name__ == '__main__':
    register_upload_routes(app, staff_list, shift_list)
    app.run(debug=True)
