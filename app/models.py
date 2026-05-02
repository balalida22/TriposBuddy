import enum
from datetime import datetime

from flask_login import UserMixin

from app.extensions import db


class SectionEnum(str, enum.Enum):
    P1 = '1P1'
    P2 = '1P2'
    P3 = '1P3'
    P4 = '1P4'


class MemberRole(str, enum.Enum):
    admin = 'admin'
    member = 'member'


class JoinRequestStatus(str, enum.Enum):
    pending = 'pending'
    approved = 'approved'
    rejected = 'rejected'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_root_admin = db.Column(db.Boolean, default=False, nullable=False)
    dark_mode = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    progress = db.relationship(
        'UserQuestionProgress',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    memberships = db.relationship(
        'GroupMembership',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    sent_join_requests = db.relationship(
        'GroupJoinRequest',
        foreign_keys='GroupJoinRequest.user_id',
        backref='requester',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    notifications = db.relationship(
        'Notification',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    invitations_created = db.relationship(
        'Invitation',
        foreign_keys='Invitation.created_by',
        backref='creator',
        lazy='dynamic',
    )
    invitations_used = db.relationship(
        'Invitation',
        foreign_keys='Invitation.used_by',
        backref='used_by_user',
        lazy='dynamic',
    )


class Invitation(db.Model):
    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    used_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_valid(self):
        return not self.revoked and self.used_by is None


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.Enum(SectionEnum), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    question_number = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('section', 'year', 'question_number', name='uq_question'),
    )

    progress = db.relationship(
        'UserQuestionProgress',
        backref='question',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    @property
    def label(self):
        return f'{self.section.value} · {self.year} · Q{self.question_number}'


class UserQuestionProgress(db.Model):
    __tablename__ = 'user_question_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    solved = db.Column(db.Boolean, default=False, nullable=False)
    solved_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'question_id', name='uq_user_question'),
    )


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, default=True, nullable=False)
    auto_approve = db.Column(db.Boolean, default=True, nullable=False)
    sat_threshold = db.Column(db.Float, default=0.667, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    memberships = db.relationship(
        'GroupMembership',
        backref='group',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    join_requests = db.relationship(
        'GroupJoinRequest',
        backref='group',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    creator = db.relationship('User', foreign_keys=[created_by])

    @property
    def member_count(self):
        return self.memberships.count()

    @property
    def admin_count(self):
        return self.memberships.filter_by(role=MemberRole.admin).count()


class GroupMembership(db.Model):
    __tablename__ = 'group_memberships'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.Enum(MemberRole), default=MemberRole.member, nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', name='uq_group_user'),
    )


class GroupJoinRequest(db.Model):
    __tablename__ = 'group_join_requests'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(
        db.Enum(JoinRequestStatus),
        default=JoinRequestStatus.pending,
        nullable=False,
    )
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
