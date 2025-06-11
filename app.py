from flask import Flask, render_template, request, redirect, flash, url_for
from instagrapi import Client
import os
import time
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

loop_active = False  # Global loop control flag
thread = None        # Global thread reference

def login_to_instagram(username, password):
    cl = Client()
    try:
        cl.login(username, password)
        return cl
    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        return None

def get_recipient_id(cl, receiver):
    try:
        if receiver.startswith("group:"):
            thread_id = receiver.split("group:")[1]
            return thread_id, True
        else:
            user_id = cl.user_id_from_username(receiver)
            return user_id, False
    except Exception as e:
        print(f"[RECIPIENT ERROR] {e}")
        return None, None

def send_looping_messages(cl, receiver, messages, delay, person_name):
    global loop_active
    recipient_id, is_group = get_recipient_id(cl, receiver)
    if not recipient_id:
        print("[ERROR] Invalid receiver.")
        return

    loop_active = True
    while loop_active:
        for msg in messages:
            if not loop_active:
                break
            full_msg = f"{person_name} {msg}"
            try:
                if is_group:
                    cl.direct_send(full_msg, [], thread_ids=[recipient_id])
                else:
                    cl.direct_send(full_msg, [recipient_id])
                print(f"[SENT] {full_msg}")
                time.sleep(delay)
            except Exception as e:
                print(f"[SEND ERROR] {e}")
                continue

@app.route('/', methods=['GET', 'POST'])
def index():
    global thread, loop_active

    if request.method == 'POST':
        if 'stop' in request.form:
            loop_active = False
            flash("🛑 Message loop stopped.")
            return redirect(url_for('index'))

        username = request.form.get('username')
        password = request.form.get('password')
        receiver = request.form.get('receiver')
        person_name = request.form.get('person_name', '').strip()
        delay = int(request.form.get('delay', 5))

        if not person_name:
            flash('❌ Person name is required.')
            return redirect('/')

        file = request.files.get('message_file')
        if not file or file.filename == '':
            flash('❌ Please upload a valid message file.')
            return redirect('/')

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            messages = [line.strip() for line in f if line.strip()]

        cl = login_to_instagram(username, password)
        if cl is None:
            flash('❌ Login failed. Check your credentials.')
            return redirect('/')

        loop_active = True
        thread = threading.Thread(target=send_looping_messages, args=(cl, receiver, messages, delay, person_name), daemon=True)
        thread.start()

        flash('✅ Message loop started. Press "Stop" to end.')
        return redirect('/')

    return render_template('index.html', loop_active=loop_active)


# ✅ Run Flask on custom port (edit port=5050 if needed)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
    