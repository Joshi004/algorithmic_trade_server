from django.db import models
from django_mysql.models import EnumField
from ats_gateway.models.User import User
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm
from trade_management_unit.Constants.TmuConstants import FREQUENCY
from trade_management_unit.lib.common.Utils.Utils import current_ist


class TradeSession(models.Model):
    class Meta:
        db_table = "trade_sessions"
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['scanning_algorithm']),
            models.Index(fields=['initiation_algorithm']),
            models.Index(fields=['termination_algorithm']),
            models.Index(fields=['trading_frequency']),
        ]
  
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False,)
    user_id = models.ForeignKey(User, to_field='public_id', on_delete=models.CASCADE, db_column='user_id')
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('paused', 'Paused'),
        ('stopped', 'Stopped'),
    ]
    status = EnumField(choices=STATUS_CHOICES, default="started")
    started_at = models.DateTimeField(blank=False)
    closed_at = models.DateTimeField(blank=True, null=True)
    dummy = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    initiation_algorithm = models.ForeignKey(InitiationAlgorithm, on_delete=models.CASCADE)
    termination_algorithm = models.ForeignKey(TerminationAlgorithm, on_delete=models.CASCADE)
    scanning_algorithm = models.ForeignKey(ScanningAlgorithm, on_delete=models.CASCADE)
    TRADING_FREQUENCY_CHOICES = [(freq, freq) for freq in FREQUENCY]

    TRADING_FREQUENCY_CHOICES = [(freq, freq) for freq in FREQUENCY]
    trading_frequency = EnumField(choices=TRADING_FREQUENCY_CHOICES, default="10-minute")

    @classmethod
    def fetch_or_create_trade_session(cls, scanning_algo_id, initiation_algo_id, termination_algo_id, trading_freq, is_dummy, user_id):
        # Validate that the algorithm IDs exist
        try:
            ScanningAlgorithm.objects.get(id=scanning_algo_id)
            InitiationAlgorithm.objects.get(id=initiation_algo_id)
            TerminationAlgorithm.objects.get(id=termination_algo_id)
        except (ScanningAlgorithm.DoesNotExist, InitiationAlgorithm.DoesNotExist, TerminationAlgorithm.DoesNotExist):
            return None, "One or more algorithm IDs are invalid"

        try:
            trade_session = cls.objects.get(
                user_id=user_id,
                scanning_algorithm_id=scanning_algo_id,
                initiation_algorithm_id=initiation_algo_id,
                termination_algorithm_id=termination_algo_id,
                trading_frequency=trading_freq,
                dummy=is_dummy
            )
            # If session already exists, return it with a message
            return trade_session, "Session already exists"
        except cls.DoesNotExist:
            # If no matching trade session is found, create a new one
            trade_session = cls(
                user_id=user_id,
                scanning_algorithm_id=scanning_algo_id,
                initiation_algorithm_id=initiation_algo_id,
                termination_algorithm_id=termination_algo_id,
                trading_frequency=trading_freq,
                status='started',  # Set status to started
                started_at=current_ist(),  # Set started_at to current timestamp
                closed_at=None,  # Set closed_at to None
                dummy=is_dummy  # Set is_dummy based on the parameter
            )
            trade_session.save()  # Save the new trade session to the database
            
            return trade_session, "New session created"

    @classmethod
    def fetch_trade_sessions(cls, session_id, status='started'):
        # Start with all trade sessions
        trade_session = cls.objects.get(id=session_id, status=status)
        # Filter by status if it's provided
        return trade_session

    @classmethod
    def fetch_active_trade_session(cls, user_id, scanning_algo_id, initiation_algo_id, termination_algo_id, trading_freq, is_dummy):
        # If user_id is a string (UUID), fetch the User instance
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                return None
        else:
            user = user_id  # Assume it's already a User instance
            
        try:
            trade_session = cls.objects.get(
                user_id=user,
                scanning_algorithm_id=scanning_algo_id,
                initiation_algorithm_id=initiation_algo_id,
                termination_algorithm_id=termination_algo_id,
                trading_frequency=trading_freq,
                dummy=is_dummy,
                status='started'
            )
            return trade_session
        except cls.DoesNotExist:
            return None

    @classmethod
    def create_trade_session(cls, user_id, scanning_algo_id, initiation_algo_id, termination_algo_id, trading_freq, is_dummy):
        # If user_id is a string (UUID), fetch the User instance
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                raise ValueError(f"User with public_id {user_id} does not exist")
        else:
            user = user_id  # Assume it's already a User instance
            
        trade_session = cls(
            user_id=user,
            scanning_algorithm_id=scanning_algo_id,
            initiation_algorithm_id=initiation_algo_id,
            termination_algorithm_id=termination_algo_id,
            trading_frequency=trading_freq,
            status='started',  # Set status to started
            started_at=current_ist(),  # Set started_at to current timestamp
            closed_at=None,  # Set closed_at to None
            dummy=is_dummy  # Set is_dummy based on the parameter
        )
        trade_session.save()  # Save the new trade session to the database
        
        return trade_session




