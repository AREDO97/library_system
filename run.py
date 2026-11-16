import click
from app import create_app, db
from app.models import User

app = create_app()

@app.cli.command("seed-admin")
def seed_admin():
    """Creates the initial Super Admin account."""
    email = "admin@library.edu"
    if User.query.filter_by(email=email).first():
        click.echo("Super Admin already exists.")
        return

    admin = User(
        name="Library Super Admin",
        email="aredoivan9@gmail.com",
        phone="+256700000000",
        role="super_admin"
    )
    admin.set_password("Admin@1234")
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Super Admin created! Login with: {email} / Admin@1234")

if __name__ == "__main__":
    app.run(debug=True, port=5000)