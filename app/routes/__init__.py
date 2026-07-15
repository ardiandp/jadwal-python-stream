def register_blueprints(app):
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.master import master_bp
    from app.routes.akademik import akademik_bp
    from app.routes.jadwal import jadwal_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(master_bp)
    app.register_blueprint(akademik_bp)
    app.register_blueprint(jadwal_bp)
