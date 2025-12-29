from flask import Blueprint, render_template

bp = Blueprint('auth', __name__)

@bp.route('/profile')
def profile():
    return render_template('profile.html')
