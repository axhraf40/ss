from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.urls import reverse
import random
import string

class CustomUser(AbstractUser):
    ROLES = [
        ('PATIENT', 'Patient'),
        ('DENTISTE', 'Dentiste'),
        ('SECRETAIRE', 'Secrétaire'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLES, default='PATIENT')
    telephone = models.CharField(max_length=15, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    adresse = models.TextField(blank=True)
    photo_profil = models.ImageField(upload_to='photos_profil/', null=True, blank=True)
    
    class Meta:
        db_table = 'auth_custom_user'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
    
    def __str__(self):
        return self.get_full_name() or self.username
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Définir les permissions de base selon le rôle
            if self.role == 'PATIENT':
                self.is_staff = False
                self.is_superuser = False
                self.is_active = True
                super().save()

class Patient(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, related_name='patient_profile')
    date_naissance = models.DateField()
    telephone = models.CharField(max_length=15)
    adresse = models.TextField()
    date_inscription = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cabinet_patient'
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Dentiste(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, related_name='dentiste_profile')
    specialite = models.CharField(max_length=100)
    telephone = models.CharField(max_length=15)
    
    class Meta:
        db_table = 'cabinet_dentiste'
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

class Secretaire(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='secretaire_profile')
    telephone = models.CharField(max_length=15)
    
    def __str__(self):
        return f"{self.user.get_full_name()}"

class RendezVous(models.Model):
    STATUT_CHOICES = [
        ('PROGRAMME', 'Programmé'),
        ('EN_COURS', 'En cours'),
        ('TERMINE', 'Terminé'),
        ('ANNULE', 'Annulé'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    dentiste = models.ForeignKey(Dentiste, on_delete=models.CASCADE)
    date_heure = models.DateTimeField()
    motif = models.CharField(max_length=200)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='PROGRAMME')
    notes = models.TextField(blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    statut_paiement = models.CharField(
        max_length=20,
        choices=[
            ('EN_ATTENTE', 'En attente'),
            ('REGLE', 'Réglé'),
        ],
        default='EN_ATTENTE'
    )
    
    class Meta:
        db_table = 'cabinet_rendez_vous'
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"
        ordering = ['-date_heure']
    
    def __str__(self):
        return f"RDV {self.patient} - {self.date_heure.strftime('%d/%m/%Y %H:%M')}"

class Consultation(models.Model):
    rendez_vous = models.OneToOneField(RendezVous, on_delete=models.CASCADE)
    diagnostic = models.TextField()
    traitement = models.TextField()
    date_consultation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Consultation {self.rendez_vous.patient} - {self.date_consultation.strftime('%d/%m/%Y')}"

class Facture(models.Model):
    STATUT_PAIEMENT = [
        ('EN_ATTENTE', 'En attente'),
        ('PAYE', 'Payé'),
        ('ECHEC', 'Échec de paiement'),
    ]
    
    MODE_PAIEMENT = [
        ('CB', 'Carte bancaire'),
        ('ESPECES', 'Espèces'),
    ]
    
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date_emission = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_PAIEMENT, default='EN_ATTENTE')
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT, null=True, blank=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    reference_transaction = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"Facture {self.consultation.rendez_vous.patient} - {self.date_emission.strftime('%d/%m/%Y')}"
    
    def get_absolute_url(self):
        return reverse('facture_detail', kwargs={'pk': self.pk})
    
    def initier_paiement_cb(self):
        if self.mode_paiement == 'CB':
            # Logique pour initier le paiement en ligne
            # À implémenter avec un service de paiement
            pass
    
    def preparer_especes(self):
        if self.mode_paiement == 'ESPECES':
            return f"Veuillez préparer {self.montant}€ en espèces."
        return ""

class Produit(models.Model):
    nom = models.CharField(max_length=200)
    description = models.TextField()
    quantite = models.IntegerField()
    seuil_alerte = models.IntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.nom
    
    def stock_faible(self):
        return self.quantite <= self.seuil_alerte

class MouvementStock(models.Model):
    TYPE_MOUVEMENT = [
        ('ENTREE', 'Entrée'),
        ('SORTIE', 'Sortie'),
    ]
    
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    type_mouvement = models.CharField(max_length=10, choices=TYPE_MOUVEMENT)
    quantite = models.IntegerField()
    date_mouvement = models.DateTimeField(auto_now_add=True)
    effectue_par = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.type_mouvement} - {self.produit.nom} - {self.quantite}"

class MembreEquipe(models.Model):
    nom = models.CharField(max_length=100)
    titre = models.CharField(max_length=100)
    specialite = models.CharField(max_length=200)
    description = models.TextField()
    photo = models.ImageField(upload_to='staff_photos/')
    ordre_affichage = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['ordre_affichage']
        verbose_name = "Membre de l'équipe"
        verbose_name_plural = "Membres de l'équipe"
    
    def __str__(self):
        return f"{self.titre} {self.nom}"

class InformationCabinet(models.Model):
    nom = models.CharField(max_length=200)
    adresse = models.TextField()
    telephone = models.CharField(max_length=15)
    email = models.EmailField()
    google_maps_url = models.URLField(help_text="URL de l'iframe Google Maps")
    description = models.TextField()
    horaires = models.TextField(help_text="Horaires d'ouverture du cabinet")
    
    class Meta:
        verbose_name = "Information du cabinet"
        verbose_name_plural = "Informations du cabinet"
    
    def __str__(self):
        return self.nom

class SpecialiteCabinet(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='specialites_images/')
    ordre_affichage = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['ordre_affichage']
        verbose_name = "Spécialité"
        verbose_name_plural = "Spécialités"
    
    def __str__(self):
        return self.nom
