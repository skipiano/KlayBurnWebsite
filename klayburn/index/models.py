from django.db import models


class Member(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=42, primary_key=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-active', 'name']

    def __str__(self):
        return self.name


class BlockData(models.Model):
    member = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True)
    date = models.DateField()
    amount = models.PositiveIntegerField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return str(self.member) + str(self.date)


class TransactionData(models.Model):
    date = models.DateField()
    amount = models.PositiveBigIntegerField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return str(self.date)


class GasFeeData(models.Model):
    date = models.DateField()
    amount = models.FloatField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return str(self.date)
