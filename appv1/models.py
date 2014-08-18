from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save


# Create your models here.
#http://blog.tivix.com/2012/01/06/extending-user-model-in-django/
# extending user model with additional attributes

class UserEnvironmentSelections(models.Model):
        abstractuser = models.ForeignKey(to='UserProfile', related_name="appselections")
        #abstractvpc = models.ForeignKey(to='UserVpc', related_name="vpcselections")
        app_url = models.URLField()
        apps_selected = models.TextField()
        subnets_selected  = models.TextField()
        columns_selected = models.TextField()
        tabs_selected = models.TextField()
        status_selected = models.TextField()

class UserVpc(models.Model):
        region = models.ForeignKey(to='UserRegion', related_name="vpc")
        vpc_selected = models.TextField()

class UserRegion(models.Model):
        user = models.ForeignKey(to='UserProfile', related_name="regions")
        region_selected = models.TextField()


class Hierarchy(models.Model):
        environment = models.TextField()
        region = models.TextField()
        vpc = models.TextField()
        subnet = models.TextField()

        class Meta:
                unique_together = (("environment","region", "vpc","subnet"),)


class SubnetOwnership(models.Model):
         hierarchy = models.ForeignKey(to='Hierarchy', related_name="subnet_ownership")
         owner = models.ForeignKey(to='UserProfile', related_name="user_owner")
         start_time = models.DateTimeField(auto_now=True)

         class Meta:
                unique_together = (("hierarchy","owner"),)


class Stack(models.Model):
        subnet = models.ForeignKey(to='Hierarchy', related_name="subnet_stack")
        stack = models.TextField()

class StackOwnership(models.Model):
        stack = models.OneToOneField(Stack)
        owner = models.TextField()
        start_time = models.DateTimeField(auto_now=True)


class StackAttributes(models.Model):
        stack = models.OneToOneField(Stack)
        attribute = models.TextField()
        attribute_value = models.TextField()
        
        class Meta:
                unique_together = (("stack", "attribute"),)

class UserConfigSelections(models.Model):
        abstractuser = models.ForeignKey(to='UserProfile', related_name="configselections")
        status_selected = models.TextField()
        envs_selected  = models.TextField()


class AbstractUser(models.Model):
        url = models.URLField()
        config_status = models.TextField()
        config_environments = models.TextField()
        region_selection = models.TextField()
        vpc_selection = models.TextField()
        subnet_selections = models.TextField()
        app_selections = models.TextField()


class UserProfile(AbstractUser):
        user = models.OneToOneField(User)
        def __str__(self):
                if self.user:
                        return "%s's profile" % self.user


def create_user_profile(sender, instance, created, **kwargs):
        if created:
                profile, created = UserProfile.objects.get_or_create(user=instance)

post_save.connect(create_user_profile, sender=User)
User.profile = property(lambda u: u.get_profile())
