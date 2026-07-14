"""AA 算账 —— Flask 应用入口."""

from flask import Flask, render_template, request, jsonify
from aa_core import settle

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/settle', methods=['POST'])
def api_settle():
    data = request.get_json(silent=True)
    if not data or 'chat_text' not in data:
        return jsonify({'error': '缺少 chat_text 字段'}), 400

    result = settle(data['chat_text'])

    return jsonify({
        'balances': {
            b.person: {
                'paid': str(b.paid),
                'share': str(b.share),
                'net': str(b.net),
            }
            for b in result.balances
        },
        'event_name': result.event_name,
        'participants': result.participants,
        'expenses': [
            {
                'payer': e.payer,
                'amount': str(e.amount),
                'description': e.description,
                'shared_by': e.shared_by if e.shared_by is not None else None,
            }
            for e in result.expenses
        ],
        'transfers': [
            {
                'from': t.from_person,
                'to': t.to_person,
                'amount': str(t.amount),
            }
            for t in result.transfers
        ],
    })


if __name__ == '__main__':
    app.run(debug=True)
