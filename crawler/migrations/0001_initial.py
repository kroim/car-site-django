# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-09-13 23:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Car',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mo_car_id', models.IntegerField(blank=True, null=True)),
                ('ove_car_id', models.IntegerField(blank=True, null=True)),
                ('ade_car_id', models.IntegerField(blank=True, null=True)),
                ('bg_car_id', models.IntegerField(blank=True, null=True)),
                ('vin', models.CharField(max_length=31)),
                ('stock_number', models.CharField(blank=True, max_length=31, null=True)),
                ('car_model', models.CharField(max_length=255)),
                ('original_price', models.IntegerField(blank=True, null=True)),
                ('final_price', models.IntegerField(blank=True, null=True)),
                ('year', models.SmallIntegerField(blank=True, null=True)),
                ('grade', models.FloatField(blank=True, null=True)),
                ('last_checking', models.DateTimeField()),
                ('is_it_available', models.BooleanField(default=True)),
                ('available_on_mo', models.BooleanField(default=False)),
                ('available_on_bg', models.BooleanField(default=False)),
                ('available_on_ove', models.BooleanField(default=False)),
                ('available_on_ade', models.BooleanField(default=False)),
                ('mo_removed_at', models.DateTimeField(blank=True, null=True)),
                ('bg_removed_at', models.DateTimeField(blank=True, null=True)),
                ('ove_removed_at', models.DateTimeField(blank=True, null=True)),
                ('ade_removed_at', models.DateTimeField(blank=True, null=True)),
                ('last_updated_time', models.DateTimeField(blank=True, null=True)),
                ('is_rejected', models.BooleanField(default=False)),
                ('rejection_reason', models.CharField(blank=True, max_length=1023, null=True)),
                ('eligible_to_display', models.BooleanField(default=False)),
                ('removed_permanently', models.BooleanField(default=False)),
                ('remain_until', models.DateTimeField(blank=True, null=True)),
                ('unique_customer_link', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CarDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detail_html', models.FilePathField()),
                ('vehicle_options', models.TextField(blank=True, null=True)),
                ('miles', models.IntegerField(blank=True, null=True)),
                ('exterior', models.CharField(blank=True, max_length=255, null=True)),
                ('interior', models.CharField(blank=True, max_length=255, null=True)),
                ('engine', models.CharField(blank=True, max_length=255, null=True)),
                ('odor', models.CharField(blank=True, max_length=255, null=True)),
                ('msrp', models.IntegerField(blank=True, null=True)),
                ('announcements', models.CharField(blank=True, max_length=1000, null=True)),
                ('value_added_options', models.CharField(blank=True, max_length=1000, null=True)),
                ('warranty_date', models.DateField(blank=True, null=True)),
                ('drive', models.CharField(blank=True, max_length=255, null=True)),
                ('keys', models.CharField(blank=True, max_length=255, null=True)),
                ('car', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='crawler.Car')),
            ],
        ),
        migrations.CreateModel(
            name='Carfax',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ownership_text', models.CharField(blank=True, max_length=255, null=True)),
                ('ownership_number', models.IntegerField(blank=True, null=True)),
                ('title_brand_text', models.CharField(blank=True, max_length=255, null=True)),
                ('title_brand_status', models.CharField(blank=True, max_length=255, null=True)),
                ('damage_text', models.CharField(blank=True, max_length=255, null=True)),
                ('damage_status', models.CharField(blank=True, max_length=255, null=True)),
                ('odometer_text', models.CharField(blank=True, max_length=255, null=True)),
                ('odometer_status', models.CharField(blank=True, max_length=255, null=True)),
                ('serviceRecords_text', models.CharField(blank=True, max_length=255, null=True)),
                ('serviceRecords_status', models.CharField(blank=True, max_length=255, null=True)),
                ('historyRecords_text', models.CharField(blank=True, max_length=255, null=True)),
                ('historyRecords_number', models.IntegerField(blank=True, null=True)),
                ('car', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crawler.Car')),
            ],
        ),
        migrations.CreateModel(
            name='CarModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('fuel_name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='CarTrim',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.CarModel')),
            ],
        ),
        migrations.CreateModel(
            name='Color',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=127)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=255, null=True)),
                ('last_name', models.CharField(blank=True, max_length=255, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=255, null=True)),
                ('email', models.CharField(blank=True, max_length=255, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('car', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Car')),
            ],
        ),
        migrations.CreateModel(
            name='Crawler',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('RUNNING', 'RUNNING'), ('IDLE', 'IDLE')], max_length=255)),
                ('last_run', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Damage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('part', models.CharField(blank=True, max_length=255, null=True)),
                ('condition', models.CharField(blank=True, max_length=255, null=True)),
                ('severity', models.CharField(blank=True, max_length=255, null=True)),
                ('estimated_price', models.IntegerField(blank=True, null=True)),
                ('mannual', models.NullBooleanField()),
                ('car', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Car')),
            ],
        ),
        migrations.CreateModel(
            name='DamageRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('part', models.CharField(default='.*', max_length=2000)),
                ('condition', models.CharField(default='.*', max_length=2000)),
                ('severity', models.CharField(default='.*', max_length=2000)),
                ('car_model', models.CharField(default='.*', max_length=2000)),
                ('price', models.IntegerField()),
                ('mannual', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link', models.URLField()),
                ('show_to_customer', models.BooleanField(default=True)),
                ('car', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Car')),
            ],
        ),
        migrations.CreateModel(
            name='Key',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('quantity', models.IntegerField(blank=True, null=True)),
                ('car', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Car')),
            ],
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('shipping_cost', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Make',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('fuel_name', models.CharField(max_length=255)),
                ('is_visible', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Repair',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('repaired', models.CharField(max_length=255)),
                ('condition', models.CharField(blank=True, max_length=255, null=True)),
                ('severity', models.CharField(blank=True, max_length=255, null=True)),
                ('repair_type', models.CharField(blank=True, max_length=255, null=True)),
                ('car', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Car')),
            ],
        ),
        migrations.CreateModel(
            name='StockImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='stock_images/')),
                ('view_type', models.CharField(choices=[('F', 'FRONT'), ('B', 'BACK'), ('S', 'SIDE')], max_length=7)),
                ('colors', models.ManyToManyField(to='crawler.Color')),
            ],
        ),
        migrations.CreateModel(
            name='StockImageInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField()),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.CarModel')),
                ('stock_image', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.StockImage')),
                ('trim', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crawler.CarTrim')),
            ],
        ),
        migrations.CreateModel(
            name='Tire',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('LFRNT', 'LFRNT'), ('LREAR', 'LREAR'), ('RFRNT', 'RFRNT'), ('RREAR', 'RREAR'), ('SPARE', 'SPARE')], max_length=31)),
                ('tread', models.CharField(blank=True, max_length=31, null=True)),
                ('brand', models.CharField(blank=True, max_length=31, null=True)),
                ('size', models.CharField(blank=True, max_length=31, null=True)),
                ('car', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Car')),
            ],
        ),
        migrations.AddField(
            model_name='damage',
            name='effective_damage_rule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crawler.DamageRule'),
        ),
        migrations.AddField(
            model_name='carmodel',
            name='make',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Make'),
        ),
        migrations.AddField(
            model_name='car',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crawler.Location'),
        ),
        migrations.AddField(
            model_name='car',
            name='make',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crawler.Make'),
        ),
        migrations.AddField(
            model_name='car',
            name='model',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crawler.CarModel'),
        ),
        migrations.AddField(
            model_name='car',
            name='trim',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crawler.CarTrim'),
        ),
    ]
