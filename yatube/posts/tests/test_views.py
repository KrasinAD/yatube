from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = PostPagesTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_show_correct_context(self):
        """Проверка правильности передоного context в шаблоны."""
        templates_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user}),
        ]
        for names in templates_names:
            response = self.guest_client.get(names)
            first_object = response.context['page_obj'][0]
            task_page = first_object.text
            task_page_author = first_object.author
            task_page_group = first_object.group
            self.assertEqual(task_page, PostPagesTests.post.text)
            self.assertEqual(task_page_author, PostPagesTests.post.author)
            self.assertEqual(task_page_group, PostPagesTests.post.group)

    def test_post_create_edit_page_show_correct_context(self):
        """Шаблоны create и post_edit сформирован с правильным контекстом."""
        templates_names = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
        ]
        for names in templates_names:
            response = self.authorized_client.get(names)
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
                'image': forms.fields.ImageField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context['form'].fields[value]
                    self.assertIsInstance(form_field, expected)

    def test_post_page_show_correct(self):
        """Проверка добавления поста на страницы."""
        templates_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user}),
        ]
        for names in templates_names:
            self.post = Post.objects.create(
                text='Тестовый пост для проверки',
                author=self.user,
                group=self.group,
            )
            response = self.authorized_client.get(names)
            first_object = response.context['page_obj'][0]
            task_page = first_object.text
            self.assertIn(self.post.text, task_page)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='test_user')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.bulk_create(
            [Post(
                text=f'Тестовый пост {i}',
                author=cls.user,
                group=cls.group,)
                for i in range(13)]
        )

    def test_paginator(self):
        """Отображение правильного кол-ва постов на страницах."""
        templates_paginator_url = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user}),
        ]
        for reverse_name in templates_paginator_url:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), 10)
                response_2 = self.guest_client.get(reverse_name + '?page=2')
                self.assertEqual(len(response_2.context['page_obj']), 3)
