from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from . import models


@receiver(pre_save, sender=models.NonRepairabilityAct)
def act_pre_save(sender, instance, *args, **kwargs):
    if instance.model:
        instance.model_description = instance.model.title


@receiver(post_save, sender=models.ActMember)
def act_member_post_save(sender, instance, *args, **kwargs):
    if instance.for_center:
        instance.act.member_for_user = instance.text
        instance.act.save(update_fields=['member_for_user'])
