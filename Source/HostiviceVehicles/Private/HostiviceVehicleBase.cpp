#include "HostiviceVehicleBase.h"

#include "HostiviceCore.h"
#include "Camera/CameraComponent.h"
#include "ChaosVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"

#define LOCTEXT_NAMESPACE "HostiviceVehicle"

AHostiviceVehicleBase::AHostiviceVehicleBase()
{
	PrimaryActorTick.bCanEverTick = true;

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(GetMesh());
	CameraBoom->TargetArmLength = 650.f;
	CameraBoom->SocketOffset = FVector(0.f, 0.f, 150.f);
	CameraBoom->bUsePawnControlRotation = true;
	CameraBoom->bEnableCameraRotationLag = true;
	CameraBoom->CameraRotationLagSpeed = 4.f;
	CameraBoom->bDoCollisionTest = true;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;

	// Bez hit eventů by nefungovalo poškození nárazem.
	GetMesh()->SetNotifyRigidBodyCollision(true);
}

void AHostiviceVehicleBase::BeginPlay()
{
	Super::BeginPlay();

	Health = MaxHealth;
	FuelLiters = FMath::Clamp(FuelLiters, 0.f, FuelCapacityLiters);

	if (LicensePlate.IsEmpty())
	{
		LicensePlate = GenerateLicensePlate();
	}

	GetMesh()->OnComponentHit.AddDynamic(this, &AHostiviceVehicleBase::OnMeshHit);
}

void AHostiviceVehicleBase::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// Palivo ubývá jen s řidičem za volantem: volnoběh 10 %, plný plyn 100 % spotřeby.
	if (Driver && IsDrivable())
	{
		const float Load = 0.1f + 0.9f * FMath::Abs(RequestedThrottle);
		FuelLiters = FMath::Max(0.f, FuelLiters - FuelConsumptionLitersPerHour * Load * DeltaSeconds / 3600.f);

		if (FuelLiters <= 0.f)
		{
			UE_LOG(LogHostivice, Log, TEXT("%s (%s): došlo palivo."), *GetName(), *LicensePlate);
			ClearDrivingInput();
		}
	}
}

void AHostiviceVehicleBase::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		UE_LOG(LogHostivice, Error, TEXT("%s: chybí UEnhancedInputComponent, vozidlo nepůjde ovládat."), *GetName());
		return;
	}

	if (ThrottleAction)
	{
		Input->BindAction(ThrottleAction, ETriggerEvent::Triggered, this, &AHostiviceVehicleBase::OnThrottle);
		Input->BindAction(ThrottleAction, ETriggerEvent::Completed, this, &AHostiviceVehicleBase::OnThrottleReleased);
	}
	if (BrakeAction)
	{
		Input->BindAction(BrakeAction, ETriggerEvent::Triggered, this, &AHostiviceVehicleBase::OnBrake);
		Input->BindAction(BrakeAction, ETriggerEvent::Completed, this, &AHostiviceVehicleBase::OnBrakeReleased);
	}
	if (SteerAction)
	{
		Input->BindAction(SteerAction, ETriggerEvent::Triggered, this, &AHostiviceVehicleBase::OnSteer);
		Input->BindAction(SteerAction, ETriggerEvent::Completed, this, &AHostiviceVehicleBase::OnSteerReleased);
	}
	if (HandbrakeAction)
	{
		Input->BindAction(HandbrakeAction, ETriggerEvent::Started, this, &AHostiviceVehicleBase::OnHandbrakeStarted);
		Input->BindAction(HandbrakeAction, ETriggerEvent::Completed, this, &AHostiviceVehicleBase::OnHandbrakeReleased);
	}
	if (LookAction)
	{
		Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AHostiviceVehicleBase::OnLook);
	}
	if (ExitAction)
	{
		Input->BindAction(ExitAction, ETriggerEvent::Started, this, &AHostiviceVehicleBase::OnExitPressed);
	}
}

// ---------------------------------------------------------------------------
// Interakce, nastupování a vystupování
// ---------------------------------------------------------------------------

void AHostiviceVehicleBase::Interact_Implementation(APawn* InteractingPawn)
{
	TryEnter(InteractingPawn);
}

FText AHostiviceVehicleBase::GetInteractionPrompt_Implementation() const
{
	if (Health <= 0.f)
	{
		return LOCTEXT("PromptWreck", "Vrak");
	}
	return bLocked ? LOCTEXT("PromptLocked", "Zamčeno") : LOCTEXT("PromptEnter", "Nastoupit");
}

bool AHostiviceVehicleBase::TryEnter(APawn* NewDriver)
{
	if (!NewDriver || NewDriver == this || Driver || bLocked || Health <= 0.f)
	{
		return false;
	}

	AController* DriverController = NewDriver->GetController();
	if (!DriverController)
	{
		return false;
	}

	// Postavu schováme a přichytíme k autu; po vystoupení ji zase ukážeme.
	// Animace nastupování a viditelný řidič přijdou až s Motion Matching sadou.
	Driver = NewDriver;
	Driver->SetActorEnableCollision(false);
	Driver->SetActorHiddenInGame(true);
	Driver->AttachToActor(this, FAttachmentTransformRules::SnapToTargetNotIncludingScale);

	DriverController->Possess(this);
	SetMappingContextActive(DriverController, true);

	OnDriverChanged.Broadcast(Driver);
	return true;
}

void AHostiviceVehicleBase::ExitVehicle()
{
	if (!Driver)
	{
		return;
	}

	AController* DriverController = GetController();
	APawn* ExitingDriver = Driver;
	Driver = nullptr;

	ClearDrivingInput();
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetHandbrakeInput(true);
	}

	// Výstup dveřmi řidiče (vlevo). Když tam není místo, zkusíme stranu spolujezdce.
	const FRotator ExitRotation(0.f, GetActorRotation().Yaw, 0.f);
	const FVector Up(0.f, 0.f, 50.f);
	FVector ExitLocation = GetActorLocation() - GetActorRightVector() * ExitOffset + Up;

	ExitingDriver->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	ExitingDriver->SetActorEnableCollision(true);
	if (!ExitingDriver->TeleportTo(ExitLocation, ExitRotation))
	{
		ExitLocation = GetActorLocation() + GetActorRightVector() * ExitOffset + Up;
		if (!ExitingDriver->TeleportTo(ExitLocation, ExitRotation))
		{
			// Obě strany blokované: postavíme postavu na místo bez kontroly kolize.
			ExitingDriver->SetActorLocationAndRotation(ExitLocation, ExitRotation);
		}
	}
	ExitingDriver->SetActorHiddenInGame(false);

	if (DriverController)
	{
		SetMappingContextActive(DriverController, false);
		DriverController->Possess(ExitingDriver);
	}

	OnDriverChanged.Broadcast(nullptr);
}

// ---------------------------------------------------------------------------
// Stav vozidla
// ---------------------------------------------------------------------------

void AHostiviceVehicleBase::ApplyVehicleDamage(float Amount)
{
	if (Amount <= 0.f || Health <= 0.f)
	{
		return;
	}

	Health = FMath::Max(0.f, Health - Amount);
	if (Health <= 0.f)
	{
		UE_LOG(LogHostivice, Log, TEXT("%s (%s): vozidlo zničeno."), *GetName(), *LicensePlate);
		ClearDrivingInput();
		OnVehicleDestroyed.Broadcast();
	}
}

void AHostiviceVehicleBase::Refuel(float Liters)
{
	FuelLiters = FMath::Clamp(FuelLiters + Liters, 0.f, FuelCapacityLiters);
}

float AHostiviceVehicleBase::GetSpeedKmh() const
{
	// GetForwardSpeed vrací cm/s; 1 cm/s = 0,036 km/h.
	const UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent();
	return Movement ? FMath::Abs(Movement->GetForwardSpeed()) * 0.036f : 0.f;
}

void AHostiviceVehicleBase::OnMeshHit(UPrimitiveComponent* HitComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit)
{
	const float Impulse = NormalImpulse.Size();
	if (Impulse > MinDamageImpulse)
	{
		ApplyVehicleDamage((Impulse - MinDamageImpulse) * ImpulseToDamage);
	}
}

// ---------------------------------------------------------------------------
// Vstup
// ---------------------------------------------------------------------------

void AHostiviceVehicleBase::OnThrottle(const FInputActionValue& Value)
{
	RequestedThrottle = IsDrivable() ? Value.Get<float>() : 0.f;
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetThrottleInput(RequestedThrottle);
	}
}

void AHostiviceVehicleBase::OnThrottleReleased(const FInputActionValue& Value)
{
	RequestedThrottle = 0.f;
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetThrottleInput(0.f);
	}
}

void AHostiviceVehicleBase::OnBrake(const FInputActionValue& Value)
{
	// Brzdit jde vždy. Couvání řeší Chaos sám (brzda ve stojícím autě = zpátečka),
	// proto bez paliva nebo s mrtvým motorem pustíme brzdu jen za jízdy.
	UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent();
	if (!Movement)
	{
		return;
	}
	const bool bRolling = FMath::Abs(Movement->GetForwardSpeed()) > 50.f;
	Movement->SetBrakeInput(IsDrivable() || bRolling ? Value.Get<float>() : 0.f);
}

void AHostiviceVehicleBase::OnBrakeReleased(const FInputActionValue& Value)
{
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetBrakeInput(0.f);
	}
}

void AHostiviceVehicleBase::OnSteer(const FInputActionValue& Value)
{
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetSteeringInput(Value.Get<float>());
	}
}

void AHostiviceVehicleBase::OnSteerReleased(const FInputActionValue& Value)
{
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetSteeringInput(0.f);
	}
}

void AHostiviceVehicleBase::OnHandbrakeStarted(const FInputActionValue& Value)
{
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetHandbrakeInput(true);
	}
}

void AHostiviceVehicleBase::OnHandbrakeReleased(const FInputActionValue& Value)
{
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetHandbrakeInput(false);
	}
}

void AHostiviceVehicleBase::OnLook(const FInputActionValue& Value)
{
	const FVector2D Look = Value.Get<FVector2D>();
	AddControllerYawInput(Look.X);
	AddControllerPitchInput(Look.Y);
}

void AHostiviceVehicleBase::OnExitPressed(const FInputActionValue& Value)
{
	ExitVehicle();
}

// ---------------------------------------------------------------------------
// Pomocné
// ---------------------------------------------------------------------------

void AHostiviceVehicleBase::SetMappingContextActive(AController* ForController, bool bActive) const
{
	const APlayerController* PC = Cast<APlayerController>(ForController);
	if (!PC || !VehicleMappingContext)
	{
		return;
	}

	if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
		ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
	{
		if (bActive)
		{
			// Priorita 1: přebije mapování pěší postavy (priorita 0).
			Subsystem->AddMappingContext(VehicleMappingContext, 1);
		}
		else
		{
			Subsystem->RemoveMappingContext(VehicleMappingContext);
		}
	}
}

void AHostiviceVehicleBase::ClearDrivingInput()
{
	RequestedThrottle = 0.f;
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetThrottleInput(0.f);
		Movement->SetBrakeInput(0.f);
		Movement->SetSteeringInput(0.f);
	}
}

FString AHostiviceVehicleBase::GenerateLicensePlate()
{
	// Formát české SPZ "1S2 3456"; S = Středočeský kraj. Písmena bez G, O, Q, W (na SPZ se nepoužívají).
	static const TCHAR Letters[] = TEXT("ABCDEFHIJKLMNPRSTUVXYZ");
	const int32 LetterCount = UE_ARRAY_COUNT(Letters) - 1;

	return FString::Printf(TEXT("%dS%c %04d"),
		FMath::RandRange(1, 9),
		Letters[FMath::RandRange(0, LetterCount - 1)],
		FMath::RandRange(0, 9999));
}

#undef LOCTEXT_NAMESPACE
