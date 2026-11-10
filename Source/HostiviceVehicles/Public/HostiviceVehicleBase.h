#pragma once

#include "CoreMinimal.h"
#include "WheeledVehiclePawn.h"
#include "HostiviceInteractable.h"
#include "HostiviceVehicleBase.generated.h"

class UCameraComponent;
class USpringArmComponent;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

/** Třída vozidla – určuje chování provozu, policie i cenu na černém trhu. */
UENUM(BlueprintType)
enum class EHostiviceVehicleClass : uint8
{
	Osobni		UMETA(DisplayName = "Osobní"),
	Dodavka		UMETA(DisplayName = "Dodávka"),
	Luxusni		UMETA(DisplayName = "Luxusní"),
	Sluzebni	UMETA(DisplayName = "Služební (policie, MHD)"),
	Uzitkove	UMETA(DisplayName = "Užitkové (traktor, multikára)")
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnVehicleDriverChanged, APawn*, NewDriver);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnVehicleDestroyed);

/**
 * Společný základ všech vozidel ve hře.
 *
 * Řeší: vstup řidiče (Enhanced Input), nastupování a vystupování,
 * palivo, poškození nárazem, zamykání a SPZ.
 * Konkrétní auta jsou Blueprinty odvozené od této třídy – v nich se nastaví
 * mesh, kola, motor a převodovka komponenty Chaos Vehicle Movement.
 */
UCLASS(Abstract)
class HOSTIVICEVEHICLES_API AHostiviceVehicleBase : public AWheeledVehiclePawn, public IHostiviceInteractable
{
	GENERATED_BODY()

public:
	AHostiviceVehicleBase();

	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	// --- IHostiviceInteractable ---
	virtual void Interact_Implementation(APawn* InteractingPawn) override;
	virtual FText GetInteractionPrompt_Implementation() const override;

	/** Posadí postavu za volant. Vrací false, pokud je auto zamčené, obsazené nebo zničené. */
	UFUNCTION(BlueprintCallable, Category = "Hostivice|Vozidlo")
	bool TryEnter(APawn* NewDriver);

	/** Vysadí řidiče vedle auta a vrátí mu ovládání. */
	UFUNCTION(BlueprintCallable, Category = "Hostivice|Vozidlo")
	void ExitVehicle();

	/** Sníží stav vozidla. Při nule motor zhasne natrvalo. */
	UFUNCTION(BlueprintCallable, Category = "Hostivice|Vozidlo")
	void ApplyVehicleDamage(float Amount);

	/** Doplní palivo (čerpací stanice na Karlovarské), ořízne na objem nádrže. */
	UFUNCTION(BlueprintCallable, Category = "Hostivice|Vozidlo")
	void Refuel(float Liters);

	UFUNCTION(BlueprintPure, Category = "Hostivice|Vozidlo")
	float GetSpeedKmh() const;

	UFUNCTION(BlueprintPure, Category = "Hostivice|Vozidlo")
	bool IsDrivable() const { return Health > 0.f && FuelLiters > 0.f; }

	UFUNCTION(BlueprintPure, Category = "Hostivice|Vozidlo")
	APawn* GetDriver() const { return Driver; }

	UPROPERTY(BlueprintAssignable, Category = "Hostivice|Vozidlo")
	FOnVehicleDriverChanged OnDriverChanged;

	UPROPERTY(BlueprintAssignable, Category = "Hostivice|Vozidlo")
	FOnVehicleDestroyed OnVehicleDestroyed;

protected:
	virtual void BeginPlay() override;

	// --- Identita ---
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Hostivice|Identita")
	FText DisplayName;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Hostivice|Identita")
	EHostiviceVehicleClass VehicleClass = EHostiviceVehicleClass::Osobni;

	/** Státní poznávací značka, např. "2SC 4817". Prázdná se vygeneruje při spawnu. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hostivice|Identita")
	FString LicensePlate;

	// --- Stav ---
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hostivice|Stav")
	bool bLocked = false;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Hostivice|Stav", meta = (ClampMin = "1"))
	float MaxHealth = 1000.f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Hostivice|Stav")
	float Health = 1000.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Hostivice|Palivo", meta = (ClampMin = "1"))
	float FuelCapacityLiters = 42.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hostivice|Palivo", meta = (ClampMin = "0"))
	float FuelLiters = 20.f;

	/** Spotřeba při plném plynu v litrech za hodinu. Volnoběh bere desetinu. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Hostivice|Palivo", meta = (ClampMin = "0"))
	float FuelConsumptionLitersPerHour = 12.f;

	// --- Poškození nárazem ---
	/** Impulz (kg·cm/s), pod kterým se náraz ignoruje. */
	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Poškození")
	float MinDamageImpulse = 150000.f;

	/** Přepočet impulzu nad prahem na body poškození. */
	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Poškození")
	float ImpulseToDamage = 0.0002f;

	// --- Nastupování ---
	/** Vzdálenost bodu výstupu vlevo od středu auta (cm). */
	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Nastupování")
	float ExitOffset = 180.f;

	// --- Kamera ---
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Hostivice|Kamera")
	TObjectPtr<USpringArmComponent> CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Hostivice|Kamera")
	TObjectPtr<UCameraComponent> FollowCamera;

	// --- Vstup (assety se přiřadí v Blueprintu) ---
	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Vstup")
	TObjectPtr<UInputMappingContext> VehicleMappingContext;

	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Vstup")
	TObjectPtr<UInputAction> ThrottleAction;

	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Vstup")
	TObjectPtr<UInputAction> BrakeAction;

	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Vstup")
	TObjectPtr<UInputAction> SteerAction;

	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Vstup")
	TObjectPtr<UInputAction> HandbrakeAction;

	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Vstup")
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(EditDefaultsOnly, Category = "Hostivice|Vstup")
	TObjectPtr<UInputAction> ExitAction;

private:
	void OnThrottle(const FInputActionValue& Value);
	void OnThrottleReleased(const FInputActionValue& Value);
	void OnBrake(const FInputActionValue& Value);
	void OnBrakeReleased(const FInputActionValue& Value);
	void OnSteer(const FInputActionValue& Value);
	void OnSteerReleased(const FInputActionValue& Value);
	void OnHandbrakeStarted(const FInputActionValue& Value);
	void OnHandbrakeReleased(const FInputActionValue& Value);
	void OnLook(const FInputActionValue& Value);
	void OnExitPressed(const FInputActionValue& Value);

	UFUNCTION()
	void OnMeshHit(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		FVector NormalImpulse, const FHitResult& Hit);

	void SetMappingContextActive(AController* ForController, bool bActive) const;
	void ClearDrivingInput();
	static FString GenerateLicensePlate();

	/** Postava, která právě řídí (schovaná a přichycená k autu). */
	UPROPERTY(Transient)
	TObjectPtr<APawn> Driver;

	float RequestedThrottle = 0.f;
};
