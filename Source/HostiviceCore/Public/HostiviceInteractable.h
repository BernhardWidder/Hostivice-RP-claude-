#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "HostiviceInteractable.generated.h"

UINTERFACE(MinimalAPI, Blueprintable)
class UHostiviceInteractable : public UInterface
{
	GENERATED_BODY()
};

/**
 * Jednotné rozhraní pro vše, s čím hráč interaguje jedním tlačítkem:
 * auta, dveře, pult ve večerce, výčep, NPC.
 */
class HOSTIVICECORE_API IHostiviceInteractable
{
	GENERATED_BODY()

public:
	/** Provede interakci. InteractingPawn je postava, která ji vyvolala. */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Hostivice|Interakce")
	void Interact(APawn* InteractingPawn);

	/** Text nápovědy v HUD, např. "Nastoupit" nebo "Dát si pivo". */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Hostivice|Interakce")
	FText GetInteractionPrompt() const;
};
