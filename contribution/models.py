from django.db import models
from django.conf import settings
# Create your models here.

class Contribution(models.Model):
    to = models.ForeignKey("project.Project", related_name='contrib_made_to', on_delete=models.CASCADE)
    #
    by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True , blank=True, on_delete=models.SET_NULL, db_index=True
    ) #allowing Contribution to be made by Anonymous 
    value = models.IntegerField(blank=True)
    # weighted mean of all reviews
    votes_power = models.IntegerField(blank=True)
    # sum of all reviewers power of vote at the moment of reviewing
    def __str__(self):
        return f"{self.by.username} -> {self.to.name}"

class Review(models.Model):

    to = models.ForeignKey(Contribution, null=True, on_delete=models.SET_NULL )
    by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True , blank=True, on_delete=models.SET_NULL, db_index=True
    ) 
    value = models.IntegerField(null=True)
    power = models.IntegerField(null=True)
    def __str__(self):
        return f"{self.by.username} reviewed {self.to}" if self.to else f"{self.by.username} -> None"
    # To do: when review is created:
    #       - [ ] - Contrib's votes_power updated by adding review.power 
    #       - [ ] - Contrib's value updated by creating a new weighted mean
    # To do: when review is deleted:
    #       - [ ] - Contrib's votes_power updated by removing review.power
    #       - [ ] - Contrib's value updated by creating a new weighted mean
    # To do: when review is updated,
    #       - [ ] - Contrib's votes_power changes if the reviewer gained/lost power of vote
    #       - [ ] - Contrib's value updated by creating a new weighted mean