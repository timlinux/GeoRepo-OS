from django.db import models

from docs.models.block import Block


class Page(models.Model):
    """Page of documentation."""

    name = models.CharField(
        max_length=512,
        help_text='Page name that will be used for frontend help center.',
        unique=True
    )

    relative_url = models.CharField(
        verbose_name='Relative Page Url',
        max_length=128,
        null=True,
        blank=True,
        help_text=(
            'Relative page url as identifier to be matched for the page that '
            'are opened. Example: put `/project`, it will use this page '
            'as help center when we are in /project.'
        )
    )

    url = models.CharField(
        verbose_name='Relative Documentation Url',
        max_length=128,
        help_text=(
            'Relative url of documentation base url that will be used as '
            '"Visit our documentation" button.'
        )
    )

    title = models.CharField(
        max_length=512,
        help_text='Title that will be used on the page help center.'
    )

    intro = models.TextField(
        null=True,
        blank=True,
        help_text=(
            'Help intro for this page help center, '
            'below title and upper of blocks.'
        )
    )

    def __str__(self):
        """String of object."""
        return self.name

    @property
    def link(self):
        """String of object."""
        from docs.models.preferences import Preferences
        return Preferences.preferences().documentation_base_url + self.url


class PageBlock(models.Model):
    """Page block"""

    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
