using UnrealBuildTool;

public class HostiviceZaCarouEditorTarget : TargetRules
{
	public HostiviceZaCarouEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_5;
		ExtraModuleNames.AddRange(new string[]
		{
			"HostiviceCore",
			"HostiviceVehicles",
			"HostiviceAI",
			"HostiviceWorld",
			"HostiviceMissions"
		});
	}
}
