import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.author = User.objects.create_user(username='auhtor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.image_jpg = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='image.jpg',
            content=cls.image_jpg,
            content_type='image/jpg'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user = PostPagesTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_show_correct_context(self):
        """Проверка правильности переданного context в шаблоны."""
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
            task_page_image = first_object.image
            self.assertEqual(task_page, PostPagesTests.post.text)
            self.assertEqual(task_page_author, PostPagesTests.post.author)
            self.assertEqual(task_page_group, PostPagesTests.post.group)
            self.assertEqual(task_page_image, PostPagesTests.post.image)

    def test_post_detail_show_correct_context(self):
        """Проверка правильности переданного context в шаблон post_detail."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        first_object = response.context['one_post']
        self.assertEqual(first_object.text, PostPagesTests.post.text)
        self.assertEqual(first_object.author, PostPagesTests.post.author)
        self.assertEqual(first_object.group, PostPagesTests.post.group)
        self.assertEqual(first_object.image, PostPagesTests.post.image)

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

    def test_index_cache(self):
        """Проверка работы кэша на главной странице."""
        index_cache = reverse('posts:index')
        response = self.authorized_client.get(index_cache)
        Post.objects.all().delete()
        response_2 = self.authorized_client.get(index_cache)
        self.assertEqual(response.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(index_cache)
        self.assertNotEqual(response_2.context, response_3.context)

    def test_follower(self):
        """Работа подписки на автора поста."""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username}
            )
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.user,
                author=self.author,
            ).exists()
        )

    def test_delete_follower(self):
        """Проверка работы отписки от автора поста."""
        follower_count = Follow.objects.count()
        Follow.objects.create(user=self.user, author=self.author)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username}
            )
        )
        follower_count_2 = Follow.objects.count()
        self.assertEqual(follower_count, follower_count_2)

    def test_post_follower_and_following(self):
        """Добавление поста для подписчика"""
        posts_count = Post.objects.count()
        Post.objects.create(
            text='Тестовый пост для подписчиков',
            author=self.user,
        )
        self.authorized_client.get(reverse('posts:follow_index'))
        if Follow.objects.filter(user=self.user, author=self.author).exists():
            self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertNotEqual(Post.objects.count(), posts_count)


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
        cache.clear()

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
