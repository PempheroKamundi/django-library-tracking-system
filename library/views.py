import datetime

from django.db.models import F
from django.template.context_processors import request
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Author, Book, Loan, Member
from .pagination import CustomPagination
from .serializers import (
    AuthorSerializer,
    BookSerializer,
    ExtendLoanSerializer,
    LoanSerializer,
    MemberSerializer,
)
from .tasks import send_loan_notification


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related("author")
    serializer_class = BookSerializer
    pagination_class = CustomPagination

    @action(detail=True, methods=["post"])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response(
                {"error": "No available copies."}, status=status.HTTP_400_BAD_REQUEST
            )
        member_id = request.data.get("member_id")
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response(
                {"error": "Member does not exist."}, status=status.HTTP_400_BAD_REQUEST
            )
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response(
            {"status": "Book loaned successfully."}, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get("member_id")
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response(
                {"error": "Active loan does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response(
            {"status": "Book returned successfully."}, status=status.HTTP_200_OK
        )


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.select_related("member")
    serializer_class = MemberSerializer

    @action(detail=True, methods=["post"], name="top-active")
    def top_active(self, request, pk=None):
        # TODO
        member = self.get_object()
        loans = Loan.objects.filter()


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.select_related("book", "member")
    serializer_class = LoanSerializer

    @action(detail=True, methods=["post"])
    def extend_due_date(self, request, pk=None):
        loan = self.get_object()
        serializer = ExtendLoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        additional_days = serializer.validated_data.get("additional_days")
        loan.due_date = F("due_date") + datetime.timedelta(days=additional_days)
        loan.save(updated_fields=["due_date"])
        
        return Response(
            {"status": "Loan date adjusted"}, status=status.HTTP_200_OK
        )
