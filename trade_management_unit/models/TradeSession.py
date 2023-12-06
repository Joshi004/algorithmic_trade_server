from django.db import models
from django_mysql.models import EnumField
from trade_management_unit.models.Algorithm import Algorithm
from trade_management_unit.models.Algorithm import AlgorithmType
from trade_management_unit.Constants.TmuConstants import FREQUENCY  # assuming constants.py is in the same directory
from trade_management_unit.lib.common.Utils.Utils import *
class TradeSession(models.Model):
    class Meta:
        db_table = "trade_sessions"
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['scanning_algorithm']),
            models.Index(fields=['tracking_algorithm']),
            models.Index(fields=['trading_frequency']),
        ]
  
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False,)
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(blank=False)
    closed_at = models.DateTimeField(blank=True, null=True)
    scanning_algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, limit_choices_to={'type': AlgorithmType.SCANNING.value}, related_name='scanning_sessions',default=1)
    tracking_algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, limit_choices_to={'type': AlgorithmType.TRACKING.value}, related_name='tracking_sessions',default=1)
    user_id = models.CharField(max_length=64, blank=False, default="1")
    dummy = models.BooleanField(default=False)

    TRADING_FREQUENCY_CHOICES = [(freq, freq) for freq in FREQUENCY]
    trading_frequency = EnumField(choices=TRADING_FREQUENCY_CHOICES, default="10minute")

    @classmethod
    def fetch_or_create_trade_session(cls, scanning_algo_name, tracking_algo_name, trading_freq, dummy, user_id):
        scanning_algo_id = Algorithm.get_id_by_name(scanning_algo_name)
        tracking_algo_id = Algorithm.get_id_by_name(tracking_algo_name)

        if scanning_algo_id is None or tracking_algo_id is None:
            # Handle the case when the algorithm name does not exist
            return None

        try:
            trade_session = cls.objects.get(
                user_id=user_id,
                scanning_algorithm_id=scanning_algo_id,
                tracking_algorithm_id=tracking_algo_id,
                trading_frequency=trading_freq,
                dummy=dummy
            )
        except cls.DoesNotExist:
            # If no matching trade session is found, create a new one
            trade_session = cls(
                user_id=user_id,
                scanning_algorithm_id=scanning_algo_id,
                tracking_algorithm_id=tracking_algo_id,
                trading_frequency=trading_freq,
                is_active=True,  # Set is_active to True
                started_at=current_ist(),  # Set started_at to current timestamp
                closed_at=None,  # Set closed_at to None
                dummy=dummy  # Set dummy based on the parameter
            )
            trade_session.save()  # Save the new trade session to the database

        return trade_session

    @classmethod
    def fetch_trade_sessions(cls,session_id, is_active=True):
        # Start with all trade sessions
        trade_session = cls.objects.get(id=session_id,is_active=is_active)
        # Filter by active if it's provided
        return trade_session


    @classmethod
    def fetch_active_trade_session(cls, user_id, scanning_algo_id, tracking_algo_id, trading_freq, dummy):
        try:
            trade_session = cls.objects.get(
                user_id=user_id,
                scanning_algorithm_id=scanning_algo_id,
                tracking_algorithm_id=tracking_algo_id,
                trading_frequency=trading_freq,
                dummy=dummy,
                is_active=True
            )
            return trade_session
        except cls.DoesNotExist:
            return None
    @classmethod
    def create_trade_session(cls, user_id, scanning_algo_id, tracking_algo_id, trading_freq, dummy):
        trade_session = cls(
            user_id=user_id,
            scanning_algorithm_id=scanning_algo_id,
            tracking_algorithm_id=tracking_algo_id,
            trading_frequency=trading_freq,
            is_active=True,  # Set is_active to True
            started_at=current_ist(),  # Set started_at to current timestamp
            closed_at=None,  # Set closed_at to None
            dummy=dummy  # Set dummy based on the parameter
        )
        trade_session.save()  # Save the new trade session to the database
        return trade_session




